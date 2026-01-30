#!/usr/bin/env python3
from starlette.formparsers import MultiPartParser
from serial.tools import list_ports
from nicegui import app, run, ui
from collections import deque
import serial
import time
import math
import logging
import asyncio
import random
import plotly.graph_objects as go
import pandas as pd
import io


#Play Data Storage
MAX_DISPLAY = 100
x_display = deque(maxlen=MAX_DISPLAY)
y_display = deque(maxlen=MAX_DISPLAY)
all_data = []

#View Settings
MultiPartParser.spool_max_size = 1024 * 1024 * 5 # 5 MB limit
SAMPLING_RATE = 80.0
PERIOD = 1.0 / SAMPLING_RATE

#DEBUG BORDERS
ui.add_head_html('''
<style>
    * {
        border: 1px solid rgba(255, 0, 0, 0.3) !important;
    }
</style>
''')

# Set the logger for pywebview to only show 'Critical' errors, hiding the warning/info noise
logging.getLogger('pywebview').setLevel(logging.CRITICAL)

#Label Coloring
rainbow_colors = ['text-red-500', 'text-orange-500', 'text-yellow-500', 'text-green-500', 'text-blue-500', 'text-indigo-500', 'text-purple-500']

#Global string storing Serial data
decoded_line= "404"
serial_num=0

#String to Integer
def extract_int(s):
    # This filters the string to keep only digits and the minus sign
    digits = ''.join([c for c in s if c == '-' or c.isdigit()])
    if not digits:
        return None # Return None if no numbers found
    try:
        return int(digits)
    except ValueError:
        return None

#View Graph Plotly Setup
view_fig = go.Figure()
view_fig.update_layout(
    title="Data Analysis",
    template="plotly_white",
    margin=dict(l=50, r=20, t=50, b=50),
    xaxis=dict(title="Time [s]"),
    yaxis=dict(title="Force [N]")
)

#Play Graph Plotly Setup
play_fig = go.Figure(data=[go.Scatter(x=[], y=[], mode='lines')])
play_fig.update_layout(
    title="Play Analysis",
    template="plotly_white",
    margin=dict(l=50, r=20, t=50, b=50),
    xaxis=dict(title="Time [s]"),
    yaxis=dict(title="Force [N]")
)

#One function to rule them all
async def all_update():
    #if tabs.value == '1':
    if ser and ser.is_open:
        # read_all() gets whatever is in the buffer right now without waiting for a newline character
        data = await run.io_bound(ser.read_all) 

        if data:
            #'backslashreplace' turns bad bytes into readable hex (e.g., \xff) 
            #'replace' turns them into the diamond question mark symbol
            decoded_line = data.decode('utf-8', errors='backslashreplace').strip()
            if decoded_line:
                serial_num=extract_int(decoded_line)
                if serial_num is not None:
                    current_time = time.time()
                    all_data.append((current_time, serial_num))
                    # Update sliding window
                    x_display.append(current_time)
                    y_display.append(serial_num)
                    # We update the trace data directly without recreating the whole layout
                    #play_plot.options['data'][0]['x'] = list(x_display)
                    #play_plot.options['data'][0]['y'] = list(y_display)
                    play_plot.update()

                with log_container:
                    ui.label(decoded_line).classes('font-mono leading-none p-0 m-0')

                if auto_scroll.value:
                    log_container.scroll_to(percent=1.0)
         

def get_ports():
    """Returns a list of available serial ports."""
    return [p.device for p in list_ports.comports()]

def toggle_connection():
    global ser
    if connection_switch.value:
        # User wants to CONNECT
        try:
            # Open the serial port with the selected options
            ser = serial.Serial(port_select.value, baudrate=baud_selecter.value, timeout=0.1)
            ui.notify(f'Connected to {port_select.value}', type='positive')        

        except Exception as e:
            ui.notify(f'Could not connect: {e}', type='negative')
            connection_switch.value = False # Reset switch
    else:
        # User wants to DISCONNECT
        if ser:
            ser.close()
            ser = None
        ui.notify('Disconnected')

def send_command():
    if ser and ser.is_open:
        # Encode string to bytes before sending
        cmd = f'{command_input.value}\n'.encode()
        ser.write(cmd)
        command_input.value = ''
    else:
        ui.notify('Not connected!', type='warning')
            
def reset_connection():
    if connection_switch.value:
        ui.notify("Connection lost due to change in Baud/Port", type='info')
        connection_switch.value=False

def clear_log():
    log_container.clear()

#Importing CSV logic (magic)
async def handle_upload(e):
    try:
        # A. Get the file name from your working snippet
        filename = e.file.name
        
        # B. Read the content
        # We try to read it. If it returns a "coroutine", we await it.
        # This makes it work regardless of whether the file wrapper is sync or async.
        content = e.file.read()
        if hasattr(content, '__await__'):
            content = await content
            
        # C. Process Data
        # content is now 'bytes'. We feed it to pandas.
        # header=None is CRITICAL because your file has no column names.
        df = pd.read_csv(io.BytesIO(content), header=None)
        
        # Extract Force (2nd column)
        # If your file has only 1 column, change this to: force = df.iloc[:, 0]
        force = df.iloc[:, 1] 
        
        # Create Time (Index * 1/80s)
        time = [i * PERIOD for i in range(len(force))]

        # D. Update Graph
        view_fig.data = []
        view_fig.add_trace(go.Scatter(x=time, y=force, mode='lines', name='Force'))
        view_fig.update_layout(title=f"File: {filename} ({len(force)} samples)")
        view_plot.update()
        
        ui.notify(f"Loaded {filename} successfully!")
        
    except Exception as err:
        ui.notify(f"Error: {str(err)}", type='negative')

#MENU
with ui.dialog() as dialog3, ui.card():

    # Main title
    with ui.row().classes('w-full justify-center mb-2'):
        ui.label('Tutorial').classes('text-4xl font-bold')
    ui.separator().classes('mb-4')

    # Main Menu
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('Main Menu').classes('text-2xl font-bold text-blue-600 mb-2')
            ui.label('This page is your starting point, it introduces the software and lets you navigate to all its key features.')\
                .classes('text-lg text-gray-700 leading-relaxed')

    # Play
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('Play').classes('text-2xl font-bold text-green-600 mb-2')
            ui.label('This is where you can record and export into a .csv the graph traced by all the Force vectors over time.')\
                .classes('text-lg text-gray-700 leading-relaxed')

    # View
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('View').classes('text-2xl font-bold text-purple-600 mb-2')
            ui.label('View allows you to ')\
                .classes('text-lg text-gray-700 leading-relaxed inline')
            ui.label('view').classes('text-lg font-bold text-purple-600 mx-1 inline')
            ui.label(' the whole graph that you recorded previously by importing a .csv.')\
                .classes('text-lg text-gray-700 leading-relaxed inline')

    # Calibration
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('Calibrate').classes('text-2xl font-bold text-orange-600 mb-2')
            ui.label('Set different weights as calibration, by default it\'s set to 500 grams.')\
                .classes('text-lg text-gray-700 leading-relaxed')

    # Serial Monitor
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('Serial Monitor').classes('text-2xl font-bold text-red-600 mb-2')
            ui.label('Essentially a debugger for your serial connection, this should be your first step to use this software.')\
                .classes('text-lg text-gray-700 leading-relaxed')

    # Credits
    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
        with ui.card_section():
            ui.label('Credits').classes('text-2xl font-bold text-indigo-600 mb-2')
            ui.label('Credits and acknowledgments for the software development.')\
                .classes('text-lg text-gray-700 leading-relaxed')

    ui.button('Close', on_click=dialog3.close)
with ui.button(icon='help', color='primary',on_click=dialog3.open).props('fab').classes('fixed bottom-4 right-4 z-50') \
.on('click', ui.dialog.open):
    ui.element().props('aria-label="Open help menu"')  
with ui.header().classes(replace='row items-center') as header:
    ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white size=lg')

with ui.left_drawer().classes('bg-blue-100 items-center') as left_drawer:
    ui.label('Torque Wizard').classes('text-3xl font-bold')
    ui.separator()
    with ui.tabs().props('vertical inline-label').classes('w-full') as tabs:
        with ui.tab('1', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('dashboard').props('size=lg')
                ui.label('Main Menu').classes('text-lg font-bold')
        with ui.tab('2', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('play_arrow').props('size=lg')
                ui.label('Play').classes('text-lg font-bold')
        with ui.tab('3', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('visibility').props('size=lg')
                ui.label('View').classes('text-lg font-bold')
        with ui.tab('4', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('balance').props('size=lg')
                ui.label('Calibrate').classes('text-lg font-bold ')
        with ui.tab('5', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('usb').props('size=lg')
                ui.label('Serial Monitor').classes('text-lg font-bold')
        with ui.tab('6', label="").classes('!justify-start'):
            with ui.row().classes('items-center'):
                ui.icon('sentiment_satisfied_alt').props('size=lg')
                ui.label('Credits').classes('text-lg font-bold')
        

with ui.tab_panels(tabs, value='1').classes('w-full'):
    with ui.tab_panel('1'):
        with ui.column().classes('items-center w-full'):
            ui.label('Main Menu').classes('text-5xl font-bold text-center w-full mb-2')
            with ui.row().classes('items-center gap-1'):
                ui.label('Welcome to ').classes('text-3xl text-center ')
                with ui.row().classes('items-center gap-0'):
                    word = "TorqueWizard"
                    for i, letter in enumerate(word):
                        color_class = rainbow_colors[i % len(rainbow_colors)]
                        ui.label(letter).classes(f'text-4xl font-bold {color_class}')
                
                ui.label('!').classes('text-3xl text-center')
            ui.label('Start by configuring your Serial with Serial Monitor!').classes('text-xl')
            ui.label('For additional information, click the help icon (?) in the bottom-left corner of the screen').classes('text-xl ')
            
                 


    with ui.tab_panel('2'):
        ui.label('Play').classes('text-5xl font-bold text-center w-full')
        ui.label('MAKE SURE THAT THE SERIAL IS WORKING!').classes('text-xl font-bold text-center w-full text-red-600')
        ui.button('Record into CSV').classes('text-xl font-bold text-center')
        play_plot = ui.plotly(play_fig).classes('w-full h-100')
        #decoded_line

    with ui.tab_panel('3'):
        ui.label('View').classes('text-5xl font-bold text-center w-full')
        ui.label('Read from CSV to get the full graph').classes('text-xl font-bold text-center w-full')
        with ui.card().classes('w-full p-4'):
            ui.upload(on_upload=handle_upload, auto_upload=True).classes('w-full mb-4')
            view_plot = ui.plotly(view_fig).classes('w-full h-96')

    with ui.tab_panel('4'):
        ui.label('Calibrate WIP').classes('text-5xl font-bold text-center w-full')
        ui.label('Send the weight with command back to the ESP using Serial Monitor').classes('text-xl font-bold text-center w-full')
        ui.label('After pressing a GPIO?').classes('text-xl font-bold text-center w-full')
        ui.label('By default the weight is 500 grams').classes('font-bold text-left w-full')
        #TODO Serial duplex communication to the ESP32 using either IDF or Arduino Framework
    
    with ui.tab_panel('5'):
        ui.label('Serial Monitor').classes('text-5xl font-bold text-center w-full')
        ser = None
        #BAUD/PORT/CONNECT/REFRESH
        with ui.row().classes('w-full items-center'):
            baud_rates=[600,1200,2400,4800,9600,14400,19200,28800,38400,57600,115200,230400]
            baud_selecter = ui.select(options=baud_rates, on_change=reset_connection, label='Baud Rates', value=baud_rates[10]).classes('w-50')
            #value é o default, por isso 115200
            port_select = ui.select(get_ports(), on_change=reset_connection, label='Select Port', value=get_ports()[0] if get_ports() else None).classes('w-50')
            ui.button(icon='refresh', on_click=lambda: port_select.set_options(get_ports())).props('flat round')
            connection_switch = ui.switch('Connect', on_change=toggle_connection)
    #Reminder never to confuse on_change=reset_connection with on_change=reset_connection(), as the latter forces Python to run it NOW!
        #SEND_COMMAND
        with ui.row().classes('w-full items-center'):
            command_input = ui.input('Send command').classes('w-105')
            command_input.on('keydown.enter', send_command)
            #Icons = https://fonts.google.com/icons?icon.set=Material+Icons&icon.style=Filled

        #SERIAL MONITOR
        with ui.row().classes('w-full items-center'):
            ui.label('Serial Monitor').classes('text-lg')
            #SCROLL
            auto_scroll = ui.switch('Auto-scroll', value=True)
            #CLEAR
            ui.button('Clear', icon='clear', on_click=clear_log).props('flat')
        #Instead of a simple Log use a Scroll Area for A not totally botched scroll
        log_container = ui.scroll_area().classes('w-full h-128 bg-gray-100 rounded border')

    with ui.tab_panel('6'):
        ui.label('Credits').classes('text-5xl font-bold text-center w-full')
        with ui.dialog() as dialog1, ui.card():
            ui.label('Victor Michels')
            ui.button('Close', on_click=dialog1.close)
        with ui.dialog().classes('w-screen h-screen bg-black/90') as dialog2, \
             ui.card().classes('w-full h-full bg-transparent border-none shadow-none p-4'):
            # Close button
            ui.button(icon='close', on_click=dialog2.close)
            # Image container
            with ui.column().classes('w-full h-full items-center justify-center'):
                ui.image('./aero.jpeg').classes('max-h-[85vh] max-w-[90vw] object-contain')

        with ui.column().classes('items-center w-full'):
            with ui.row().classes('items-center'):
                ui.button('Developed by:', on_click=dialog1.open)
                ui.button('Developed to:', on_click=dialog2.open)
            with ui.row().classes('items-center gap-1'):
                ui.label('Based on this')
                ui.label('fantastic').classes('font-bold italic font-[Comic_Sans_MS]')
                ui.label('idea:')
            ui.image('./plano.png').classes('w-full max-w-4xl h-auto mx-auto')

#1/80 = 0.0125
ui.timer(0.0125, all_update) #polling rate to run read_loop

ui.run(title="ToqueWizard")
#if __name__ in {"__main__", "__mp_main__"}:
#    ui.run(
#        native=True, 
#        window_size=(800, 600), 
#        title="oqueWizard",
#        reload=False
#    )ui.run()