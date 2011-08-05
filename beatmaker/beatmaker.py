#!/usr/bin/env python

import pygame
from optparse import OptionParser
from pygame.locals import *
from pygame.midi import *
from pygame.time import *
from midiutil.MidiFile import MIDIFile

# main method
def main():
    parser = OptionParser()
    parser.add_option("-b", "--bpm", dest="bpm",
                  help="BPM of music", type="int", default=140)
    parser.add_option("-c", "--continous", dest="continous",
                  action="store_true", help="Should notes be continous?", default=True)
    parser.add_option("-s", "--min", dest="min",
                  help="Minimal length of quantatized note 1/x->you speciffic x", type="int", default=8)
    parser.add_option("-f", "--full", dest="full",
                  action="store_true", help="Only full notes", default=False)
    parser.add_option("-o", "--output", dest="output",
                  help="Prefix of output file", type="string", default="beatmaker_")
    (options, args) = parser.parse_args()

    print "Usage: E to erase whole recording session, D to delete only current session, R to store current session, \
Q to quantatize and write out and ESC to quit."

    pygame.display.init()
    pygame.midi.init()
    pygame.font.init()

    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('beatmaker')
    pygame.mouse.set_visible(0)
    background = pygame.Surface((screen.get_width(), screen.get_height()))

    beat_colors=[(255,255,0),(255,255,0),(255,255,0),(0,255,255)]
    myfont = pygame.font.SysFont("Comic Sans MS", 400)
    beat_label = myfont.render("1", 1, beat_colors[0])
    screen.blit(beat_label, (200, 0))

    pygame.display.flip()

    midi= Output(2)
    tempo= options.bpm
    beat=60000/tempo

    sum= 0
    on= True
    done = False
    last_num=0
    num=0

    latency= 200

    events= []
    tick_times= []
    master_tick_times= []
    repeated_events=[]
    write_id= 0

    pygame.init()
    offset= get_ticks()

    #Main loop
    while not done:
        time=get_ticks()-offset

        #Handling of graphics
        if(num!=last_num and on and on_time+latency==get_ticks()):
            screen.blit(background, (0,0))
            beat_label = myfont.render(str(num), 1, beat_colors[num-1])
            screen.blit(beat_label, (200, 0))
            pygame.display.flip()

        #Handling of metronome
        if(abs(time-beat/2)<10 and not on):
            if num==4:
                midi.note_off(46,channel=9)
            else:
                midi.note_off(50,channel=9)
            on= True
            on_time= get_ticks()
        elif(abs(time-beat)<10 and on):
            tick= get_ticks()
            if num==4:
                midi.note_on(46,127,9)
                num=0
                master_tick_times.append(tick)
            else:
                midi.note_on(50,127,9)
            tick_times.append(tick)
            offset=tick
            on= False
            last_num= num
            num+= 1

        #Handling of key events
        for event in pygame.event.get():
            if (event.type == KEYUP) or (event.type == KEYDOWN):
                #On any key press we append note direction and time to events
                if event.type == KEYDOWN:
                    events.append((0,get_ticks()))
                elif event.type == KEYUP:
                    events.append((1,get_ticks()))

                #Erase whole progression
                if (event.key == K_e and event.type == KEYDOWN):
                    repeated_events= []
                #Delete current progression
                if (event.key == K_d or event.key == K_e and event.type == KEYDOWN):
                    events= []
                    tick_times= []
                #Save current progression to recording
                if (event.key == K_r and event.type == KEYDOWN):
                    print "Append"
                    repeated_events.append((events[:],tick_times[:],master_tick_times[:]))
                    events= []
                    tick_times= []
                #Quantatize and save to output
                if (event.key == K_q and event.type == KEYDOWN):
                    quantatizations= []
                    statistics= []

                    #We make statistics based on all older progressions,
                    #remember that note lenghts must match or system will sellect those
                    #progressions with matched note lengths.
                    for (levents, ltick_times, lmaster_tick_times) in repeated_events:
                        quantatizations.append( Quantatize(ltick_times, lmaster_tick_times, levents, options.min, 0, True, options.full) )

                    #Create statistics table of number counts that speciffc notes occur
                    #on speciffc places.
                    for y, quantatization in enumerate(quantatizations):
                        for x, note in enumerate(quantatization):
                            (name, time, length)= note
                            print "X is: ", x
                            if len(statistics)<=x:
                                statistics.append({})
                                statistics[x][name]= {"count": 1, "note": note}
                            else:
                                if note in statistics[x]:
                                    statistics[x][name]["count"]+=1

                    #Make results and select note that occures most on speciffic place.
                    #TODO: If speciffic note occurs the same time as another group of note,
                    #      we should select note based on how mouch it differs from middle point.
                    result= []
                    for x, note_id in enumerate(statistics):
                        max= 0
                        for note_key in note_id:
                            note= note_id[note_key]
                            if note["count"]>max:
                                max= note["count"]
                                max_note= note["note"]
                        print "Note ", x, " is ", max_note
                        result.append(max_note)

                    WriteMidi(result, options.bpm, options.output+str(write_id)+".mid")
                    write_id+= 1
                #On exit
                if (event.key == K_ESCAPE):
                    done = True

def Quantatize(tick_times, beat_times, events, min_length, max_length, continous, full_notes=True):
    offset= 0
    on_time= 0
    off_time= 0
    last_on_time= 0
    note_times= []
    found_notes= []

    print "Min note length is 1/", min_length
    print "Only full notes? ", full_notes
    
    #Calculate avrage length of 1/4 beat.
    sum= 0
    tick1= tick_times[0]
    for time in tick_times[1:]: 
        sum+= time-tick1
        tick1= time
    avg_beat_len= sum/(len(tick_times)-1)
    print "Avrage beat length is: ", avg_beat_len

    #Make as many stick points as minimal note length, it cannot be smaller than 1/4
    new_tick_times=[]
    tick1= tick_times[0]
    for time in tick_times[1:]:
        add= (time-tick1)/(min_length/4)
        for x in range(0,(min_length/4)): new_tick_times.append(time+add*x)
        tick1= time
    tick_times= new_tick_times
    
    #Calculate note lengths based on length of beat
    notes=[("1",avg_beat_len*4,1.0),
           ("1*",avg_beat_len*4+avg_beat_len*2, 1.+1./2.),
           ("1+1/4",avg_beat_len*4+avg_beat_len, 1.+1./4.),
           ("1/2",avg_beat_len*2, 1./2.),
           ("1/2+1/8",avg_beat_len*2+avg_beat_len/2, 1./2.+1./8.),
           ("1/2*",avg_beat_len*2+avg_beat_len, 1./2.+1./4.),
           ("1/4",avg_beat_len, 1./4.),
           ("1/4+1/16",avg_beat_len+avg_beat_len/4, 1./4.+1./16.),
           ("1/4*",avg_beat_len+avg_beat_len/2, 1./4.+1./2.),
           ("1/8",avg_beat_len/2, 1./8.),
           ("1/8*",avg_beat_len/2+avg_beat_len/4, 1./8.+1./16.),
           ("1/16",avg_beat_len/4, 1./16.),
           ("1/16*",avg_beat_len/4+avg_beat_len/8, 1./16.+1./32.)]

    for (name,time,length) in notes:
        print "Note name: ", name, "time: ", time, "length: 1/", (length)**(-1.)
    
    last_bar_time= 0
    for dir, event_time in events:
        offset= FindClosestTick(event_time, tick_times)
        
        print "Event time was ", event_time, "Closest thick is ", offset
        if dir==0: #Down
            on_time= offset
            if continous:
                if last_on_time!=0:
                    note_times.append((last_on_time, on_time))
                    min=notes[0][1]
                    last_name= ""
                    print on_time-last_on_time
                    for id, note in enumerate(notes):
                        (name, time, length)= note
                        if full_notes:
                            if "*" in name or "+" in name:
                                continue
                        if abs((on_time-last_on_time)-time)<min:
                            min= abs((on_time-last_on_time-10)-time)
                            last_note= note
                    last_on_time= 0
                    found_notes.append(last_note)
                last_on_time= on_time
        if dir==1: #Up
            off_time= offset
            if not continous:
                note_times.append((on_time, off_time))
                min=notes[0][1]
                last_name= ""
                for id, note in enumerate(notes):
                    (name, time, length)= note
                    if abs((off_time-on_time)-time)<min:
                        min= abs((off_time-on_time)-time)
                        last_note= note
                found_notes.append(last_note)
    return found_notes

def WriteMidi(notes, tempo, file):
    MyMIDI = MIDIFile(1)

    MyMIDI.addTrackName(0,0,"Sample Track")
    MyMIDI.addTempo(0,0,tempo)

    time= 0
    for (name, d, length) in notes:
        MyMIDI.addNote(0,0,60,time,length*4,100)
        time+= length*4

    binfile = open(file, 'wb')
    MyMIDI.writeFile(binfile)
    binfile.close()

def FindClosestTick(event_time, tick_times):
    min= 100000
    for id,tick_time in enumerate(tick_times):
        if abs(event_time-tick_time)<min:
            min= abs(event_time-tick_time)
            offset= id
    return tick_times[offset]

def GetBarTime(event_time, bar_times):
    min= 100000
    for id, bar_time in enumerate(bar_times):
        if abs(event_time-bar_time)<min:
            min= abs(event_time-bar_time)
            offset= id

    return bar_times[offset]

# allow use as a module or standalone script
if __name__ == "__main__":
    main()
