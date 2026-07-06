"""
imagine的に太陽を撮影
断りが無ければ座標の原点は写真の中央です。
"""
import numpy as np
import time 

# ==parameters==
# 単位はpixel
image_size=(1608,1104)
sun_radius=150
mobility_factor=0.1#太陽の見かけ上の移動量。1sでsun_radiusの何倍移動するか。pixel/s
far=500#画像中心から太陽中心までの距離
#単位はラジアン
cam_rotate=2#0なら東西がそろっています。

# boolean
equatorial_mount=True
take_center=True

def create_pic(place,radius,im_size):
    pic=np.array([[]])


stomp=time.time()
while True:
    operation_rotate=float(input())#未制作。標準入力ではなく、ユーザが1frameの間にカメラを回した量。
    now_time=time.time()
    
    took_time=now_time-stomp

    cam_rotate+=operation_rotate

    if take_center:
        far-=mobility_factor*sun_radius*2*took_time
        if far<0:
            far=0

    if not equatorial_mount:
        far+=mobility_factor*sun_radius*2*took_time
    
    place=np.cos(cam_rotate)*far, np.sin(cam_rotate)*far

    if max([image_size[i]/2- abs(place[i]) for i in range(2)])>sun_radius*0.6:
        print("太陽が画面外に出ました。")
        time.sleep(0.5)
        far=0

    picture=create_pic(place,sun_radius,image_size)
