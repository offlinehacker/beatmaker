#!/usr/bin/env python

import pygame
from optparse import OptionParser
from pygame.locals import *
from pygame.midi import *
from pygame.time import *

# main method
def main():
    parser = OptionParser()
    parser.add_option("-i", "--ip", dest="ip",
                  help="IP address of car", type="string", default="127.0.0.1")
    parser.add_option("-p", "--port", dest="port",
                  help="Port of car", type="int", default=64100)
    parser.add_option("-1", "--max1", dest="m1",
                  help="Max value for servo 1", type="int", default=5)
    parser.add_option("-2", "--max2", dest="m2",
                  help="Max value for servo 2", type="int", default=10)
    (options, args) = parser.parse_args()
    
    pygame.display.init()
    pygame.midi.init()
    
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('Pygame Caption')
    pygame.mouse.set_visible(0)
    
    midi= Output(2)
    midi.set_instrument(0)
    
    tempo= 160
    beat=60000/(tempo)
    
    sum= 0
    on= True
    
    done = False
    num=0
    
    events= []
    tick_times= []
    master_tick_times= []
    
    pygame.init()
    offset= get_ticks()
    while not done:
        time=get_ticks()-offset
        if(abs(time-beat/2)<2 and not on):
            print "off"
            if num==4:
                midi.note_off(46,channel=9)
            else: 
                midi.note_off(50,channel=9)
            on= True
        elif(abs(time-beat)<2 and on):
            print "on"
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
            num+= 1
        for event in pygame.event.get():
            if (event.type == KEYUP) or (event.type == KEYDOWN):
                #print event
                if event.type == KEYDOWN:
                    events.append((0,get_ticks()))
                elif event.type == KEYUP:
                    events.append((1,get_ticks()))
                if (event.key == K_e):
                    events= []
                    tick_times= []
                if (event.key == K_ESCAPE):
                    print events
                    print tick_times
                    print Quantatize(tick_times, master_tick_times, events, 0 ,0, True)
                    done = True
                    
def Quantatize(tick_times, master_tick_times, events, min_length, max_length, continous, full_notes=True):
    offset= 0
    on_time= 0
    off_time= 0
    last_on_time= 0
    note_times= []
    found_notes= []
    
    sum= 0
    tick1= tick_times[0]
    for time in tick_times[1:]: 
        print "Beat length: ", time-tick1 
        sum+= time-tick1
        tick1= time
    avg_beat_len= sum/(len(tick_times)-1)

    new_tick_times=[]
    tick1= tick_times[0]
    for time in tick_times[1:]:
        add= (time-tick1)/8
        for x in range(0,8): new_tick_times.append(time+add*x)
        tick1= time
    tick_times= new_tick_times
    
    #Calculate note lengths based on length of beat
    notes=[("1",avg_beat_len*4),
           ("1*",avg_beat_len*4+avg_beat_len*2),
           ("1/2",avg_beat_len*2),
           ("1/2*",avg_beat_len*2+avg_beat_len),
           ("1/4",avg_beat_len),
           ("1/4*",avg_beat_len+avg_beat_len/2),
           ("1/8",avg_beat_len/2),
           ("1/8*",avg_beat_len/2+avg_beat_len/4),
           ("1/16",avg_beat_len/4),
           ("1/16*",avg_beat_len/4+avg_beat_len/8),]
    for (name,note) in notes:
        print "Note time: ", name, "len: ", note
    
    last_bar_time= 0
    for dir, event_time in events:
        offset= FindClosestTick(event_time, tick_times)
        bar_time= GetBarTime(event_time, master_tick_times)
        
        print "Event time was ", event_time, "Closest thick is ", offset
        if dir==0: #Down
            on_time= offset
            if continous:
                if last_on_time!=0:
                    note_times.append((last_on_time, off_time))
                    min=notes[0][1]
                    last_name= ""
                    print on_time-last_on_time
                    for id, (name, x) in enumerate(notes):
                        if full_notes:
                            if "*" in name:
                                continue
                        if abs((on_time-last_on_time)-x)<min:
                            min= abs((on_time-last_on_time)-x)
                            last_name= name
                    last_on_time= 0
                    found_notes.append(last_name)
                last_on_time= on_time
        if dir==1: #Up
            off_time= offset
            if not continous:
                note_times.append((on_time, off_time))
                min=notes[0][1]
                last_name= ""
                for id, (name, x) in enumerate(notes):
                    if abs((off_time-on_time)-x)<min:
                        min= abs((off_time-on_time)-x)
                        last_name= name
                found_notes.append(last_name)
                                   
    return found_notes
                
    
                
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
