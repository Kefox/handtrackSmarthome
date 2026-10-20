import mediapipe as mp
import cv2 as cv
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

PROXY_HM_ADDRESS = os.getenv("PROXY_HM_ADDRESS")
PROXY_HMIP_ADDRESS = os.getenv("PROXY_HMIP_ADDRESS")

proxy_hm = xmlrpc.client.ServerProxy(PROXY_HM_ADDRESS)
proxy_hmip = xmlrpc.client.ServerProxy(PROXY_HMIP_ADDRESS)

circle_id = None
pointer_cooldown = 0
lights = [False, False]
shutter = False
clicked = False

current_color = "red"

debug = False

camera = cv.VideoCapture(0)
camera.set(cv.CAP_PROP_FRAME_WIDTH, 320)
camera.set(cv.CAP_PROP_FRAME_HEIGHT, 240)
camera.set(cv.CAP_PROP_BUFFERSIZE, 1)

mp_hands = mp.solutions.hands
mp_drawing_styles = mp.solutions.drawing_styles
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,

    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def update_pointerpos(image):
    global clicked, circle_id, pointer_cooldown, lights, click_holddown, debug, shutter, current_color

    image.flags.writeable = False
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    results = hands.process(image)

    if results.multi_hand_landmarks:
        hand_zero = results.multi_hand_landmarks[0]
        index = hand_zero.landmark[8]
        thumb = hand_zero.landmark[4]
        
        indices = [0, 1, 2, 5, 9, 13, 17]
        center_x = sum(hand_zero.landmark[i].x for i in indices) / len(indices)
        center_y = sum(hand_zero.landmark[i].y for i in indices) / len(indices)
                    
        h, w, c = image.shape
                    
        ix = int(index.x * w)
        iy = int(index.y * h)
        iz = int(index.z * w)
        tx = int(thumb.x * w)
        ty = int(thumb.y * h)
        tz = int(thumb.z * w)
        
        scrx = int(center_x * screen_width)
        scry = int(center_y * screen_height)
        
        r = 40
        hovered_bool = is_hovered(scrx, scry, r)
        
        dist = math.sqrt((ix-tx)**2+(iy-ty)**2+(iz-tz)**2)
            

        if dist <= 20:
            color = "green"
            if clicked == False:
                if hovered_bool == "button_Schreibtisch":
                    if lights[0] == False:
                        lights[0] = True
                        update_real_light("Schreibtisch", True)
                        update_bg()
                    else:
                        lights[0] = False
                        update_real_light("Schreibtisch", False)
                        update_bg()

                if hovered_bool == "button_Bett":
                    if lights[1] == False:
                        lights[1] = True
                        update_real_light("Bett", True)
                        update_bg()
                    else:
                        lights[1] = False
                        update_real_light("Bett", False)
                        update_bg()

                if hovered_bool == "button_Rollo":
                    if shutter == False:
                        shutter = update_real_shutter(0.0)
                        update_bg()
                    else:
                        shutter = update_real_shutter(1.0)
                        update_bg()
                clicked = True
        else:
            clicked = False
            if hovered_bool in ["button_Rollo", "button_Bett", "button_Schreibtisch"]:
                color = "blue"
            else:
                color = "red"
    
        canvas.itemconfig(circle_id, state="normal")
        canvas.coords(circle_id, scrx-r, scry-r)  
        if current_color != color: 
            canvas.itemconfig(circle_id, image=tk_circle_img[color])   
            current_color = color  
    
        if debug == True:
            print("x: " + str(scrx) + ", y:" + str(scry))
    
    else:
        canvas.itemconfig(circle_id, state="hidden")

    window.after(1, evaluate_camera)

def evaluate_camera():
    if camera.isOpened():
            success, image = camera.read()
            if not success:
                print("Empty frame")
            else:
                image = cv.flip(image, 1)
                update_pointerpos(image)

def exit_program(e):
    camera.release()
    window.destroy()

def create_pointer(r, color):
    circle_img = Image.new("RGBA", (2*r, 2*r), (0, 0, 0, 0))
    draw = ImageDraw.Draw(circle_img)
    
    outer_color = (color[0], color[1], color[2], color[3] // 2)
    draw.ellipse([0, 0, 2*r, 2*r], fill=outer_color)
    
    border = 12
    draw.ellipse([border, border, 2*r - border, 2*r - border], fill=color)
    return ImageTk.PhotoImage(circle_img)

def is_hovered(scrx, scry, r):
    desk_x = 0.4687 * screen_width
    desk_y = 0.3472 * screen_height
    if (desk_x - r <= scrx < desk_x + r) and (desk_y - r <= scry < desk_y + r):
        return "button_Schreibtisch"
    
    bed_x = 0.5469 * screen_width
    bed_y = 0.5556 * screen_height
    if (bed_x - r <= scrx < bed_x + r) and (bed_y - r <= scry < bed_y + r):
        return "button_Bett"

    if (0.4297 * screen_width <= scrx < 0.5078 * screen_width) and (0.4861 * screen_height <= scry < 0.6944 * screen_height):
        return "button_Rollo"
    
def update_bg():
        state = (lights[0], lights[1], shutter)
        canvas.itemconfig(bg_id, image=bg_images[state])

BETT_ID = os.getenv("BETT_ID")
SCHREIBTISCH_ID = os.getenv("SCHREIBTISCH_ID")

def update_real_light(light_id, state):
    global proxy_hmip

    light_id_dic = {
        "Bett": BETT_ID,
        "Schreibtisch": SCHREIBTISCH_ID,
    }

    proxy_hmip.setValue(light_id_dic[light_id], "STATE", state)
    print("Licht " + str(light_id) + " wird auf " + str(state) + " gesetzt")

def get_real_light():
    global proxy_hmip

    light_id_dic = {
            "Bett": BETT_ID,
            "Schreibtisch": SCHREIBTISCH_ID,
        }
    
    res_Bett = proxy_hmip.getValue(light_id_dic["Bett"], "STATE")
    res_Schreibtisch = proxy_hmip.getValue(light_id_dic["Schreibtisch"], "STATE")
    print("Licht Bett ist auf " + str(res_Bett) + " gesetzt")
    print("Licht Schreibtisch ist auf " + str(res_Schreibtisch) + " gesetzt")

    return [res_Schreibtisch, res_Bett]

SHUTTER_ID = os.getenv("SHUTTER_ID")

def update_real_shutter(level):
    global proxy_hm
    id = SHUTTER_ID

    if level == 1.0:
        updated_status = False
    if level == 0.0:
        updated_status = True

    try:
        proxy_hm.setValue(id, "LEVEL", level)
        print("Rollo " + str(id) + " wird auf " + str(level) + " gesetzt")
        return updated_status
    except xmlrpc.client.Fault as fault:
        print("Fehler: " + str(fault))
        return not updated_status
    except Exception as err:
        print("Fehler: " + str(err))
        return not updated_status

def get_real_shutter():
    global proxy_hm
    id = SHUTTER_ID

    try:
        level = proxy_hm.getValue(id, "LEVEL")
        print("Rollo " + str(id) + " ist auf " + str(level) + " gesetzt")
        if level == 0.0:
            return True
        else:
            return False
    except xmlrpc.client.Fault as fault:
        print("Fehler: " + str(fault))
        return False
    except Exception as err:
        print("Fehler: " + str(err))
        return False

def change_debug_mode(e):
    global debug
    if debug == True:
        debug = False
    else:
        debug = True

window = tk.Tk()
window.title("Smart Home Steuerung")
window.attributes("-fullscreen", True)
window.bind_all("<Escape>", exit_program)
window.bind_all("d", change_debug_mode)
window.config(cursor="none")
window.after(100, evaluate_camera)

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

canvas = tk.Canvas(
    window, 
    width=screen_width, 
    height=screen_height, 
    bg="white", 
    bd=0, 
    highlightthickness=0
)
canvas.pack(fill="both", expand=True)

prefix_hidden = "images/shutter_hidden/renders/"
prefix_shown = "images/shutter_shown/renders/"
bg_images = {
    (False, False, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "base.png").resize((screen_width, screen_height))),
    (True, False, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    (False, True, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Bett.png").resize((screen_width, screen_height))),
    (True, True, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Bett_light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    
    (False, False, True): ImageTk.PhotoImage(Image.open(prefix_shown + "base.png").resize((screen_width, screen_height))),
    (True, False, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    (False, True, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Bett.png").resize((screen_width, screen_height))),
    (True, True, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Bett_light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
}

bg_id = canvas.create_image(0, 0, image=bg_images[(False, False, False)], anchor="nw")
lights = get_real_light()
shutter = get_real_shutter()
update_bg()


tk_circle_img = {
    "red": create_pointer(40, (255, 0, 0, 128)),
    "green": create_pointer(40, (0, 255, 0, 128)),
    "blue": create_pointer(40, (87, 185, 255, 128))
}
circle_id = canvas.create_image(0, 0, image=tk_circle_img["red"], anchor="nw")
canvas.itemconfig(circle_id, state = "hidden")

window.mainloop()




