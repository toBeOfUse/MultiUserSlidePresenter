import socketio
import tornado.web as tn
import tornado.ioloop as tnio
import os
import asyncio
import sys
import glob
import subprocess

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # required for tornado in python 3.8

sio = socketio.AsyncServer(async_mode='tornado')
static = os.path.join(os.getcwd(), "static\\")
server = tn.Application([
    (r"/socket\.io/", socketio.get_tornado_handler(sio)),
    (r"/(.*)", tn.StaticFileHandler, {"default_filename": "index.html", "path": static})
])

slide_state = {
    "presentation": "",
    "current_slide": 1,
    "total_slides": 0
}

laser_state = {
    "laser_controller": "",
    "laser_x": -1,
    "laser_y": -1
}


@sio.event
def connect(sid, environ):
    print('connected a client')
    asyncio.create_task(sio.emit('presentation_change', data=slide_state, room=sid))
    if laser_state["laser_controller"] and 0 <= laser_state['x'] <= 1 and 0 <= laser_state['y'] <= 1:
        asyncio.create_task(sio.emit('draw_laser', laser_state))


@sio.event
def disconnect(sid):
    if sid == laser_state["laser_controller"]:
        laser_state["laser_controller"] = ""
        asyncio.create_task(sio.emit('hide_laser'))


@sio.event
def slide_change(sid, new_slide):
    if 0 < new_slide < slide_state['total_slides']:
        slide_state["current_slide"] = new_slide
        asyncio.create_task(sio.emit('presentation_change', data=slide_state, skip_sid=sid))


@sio.event
def laser_on(sid, data):
    laser_state["laser_controller"] = sid
    asyncio.create_task(sio.emit('surrender_laser', skip_sid=sid))


@sio.event
def laser_off(sid, data):
    if sid == laser_state["laser_controller"]:
        laser_state["laser_controller"] = ""
    asyncio.create_task(sio.emit('hide_laser'))


@sio.event
def laser_update(sid, data):
    if sid == laser_state["laser_controller"] and "x" in data and "y" in data:
        laser_state["laser_x"] = data["x"]
        laser_state["laser_y"] = data["y"]
        if 0 <= data["x"] <= 1 and 0 <= data["y"] <= 1:
            asyncio.create_task(sio.emit('draw_laser', data, skip_sid=sid))
        else:
            asyncio.create_task(sio.emit('hide_laser', skip_sid=sid))


if __name__ == "__main__":
    print('hello!')
    presentations = glob.glob(os.path.join(static, 'slides\\')+'*.pdf')
    for presentation in presentations:
        folder = presentation[:-4]
        presentation_name = os.path.split(folder)[1]
        slide_state["presentation"] = presentation_name
        if not os.path.isdir(folder):
            print('generating png slides for '+presentation_name+'...')
            os.mkdir(folder)
            subprocess.check_output(['pdftocairo', '-png', presentation, os.path.join(folder, 'slide')])
            print('done!')
        slide_state["total_slides"] = len(glob.glob(os.path.join(folder, '*.png')))
    server.listen(4567)
    print('starting tornado server...')
    tnio.IOLoop.current().start()
