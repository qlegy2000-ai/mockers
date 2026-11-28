import sys, os, subprocess
sys.path.insert(0,'/home/user/mockers')
from compose_v2 import LANDMARKS
from PIL import Image, ImageDraw, ImageFont
S=os.path.dirname(os.path.abspath(__file__)); os.chdir(S); O='ads'
Y=(251,205,6); K=(12,12,12); W=(255,255,255)
F=lambda s,w="Black": ImageFont.truetype(subprocess.check_output(["fc-match","-f","%{file}",f"Inter Display:style={w}"]).decode(),s)
PICKS=[("b4","old-people","Hoodie","Black"),("b3","the-nicest-asshole","Sweatshirt","DarkBlue"),("b3","word-filter","Hoodie","Black"),
 ("b4","rock-paper-liquor","Hoodie","Purple"),("b3","i-choose-violance","Hoodie","Black"),("b3","kill-bic","Sweatshirt","Black"),
 ("b4","tequla","Hoodie","AegeanBlue"),("b3","breaking-sad","Hoodie","Purple"),("b4","millennials","Sweatshirt","DarkBlue"),
 ("b3","im-not-judgemantal","Sweatshirt","DarkBlue"),("b3","wtf","Hoodie","Black"),("b3","trans-parent","Hoodie","Purple")]
def crop(b,d,s,c,ratio=1.25,zoom=1.15):
    im=Image.open(f"{b}/{d}_{s}_{c}.jpg").convert("RGB"); neck,cw,cx=LANDMARKS[(s,c)]
    w=zoom*cw; h=w*ratio; top=neck-0.28*w; x0=cx-w/2
    x0=min(max(x0,0),im.width-w); top=min(max(top,0),im.height-h)   # never crop outside the photo
    return im.crop((int(x0),int(top),int(x0+w),int(top+h)))
def text_c(dr,xy_w,y,t,f,fill):
    x0,wid=xy_w; tw=dr.textlength(t,font=f); dr.text((x0+(wid-tw)/2,y),t,font=f,fill=fill)
OFFER=["FREE SHIPPING","ALL OVER EGYPT"]
# ---------- 1) Reel frames 1080x1920 ----------
fr=f"{O}/reel"; os.makedirs(fr,exist_ok=True)
def frame_photo(i,img,top_line,bottom):
    f=Image.new("RGB",(1080,1920),K); ph=img.resize((1080,1350)); f.paste(ph,(0,285)); dr=ImageDraw.Draw(f)
    dr.rectangle((0,0,1080,285),fill=Y); text_c(dr,(0,1080),95,top_line,F(78),K)
    text_c(dr,(0,1080),1690,bottom,F(56,"Bold"),W); f.save(f"{fr}/{i:02d}.png")
def frame_text(i,lines,bg=Y,fg=K,sizes=None):
    f=Image.new("RGB",(1080,1920),bg); dr=ImageDraw.Draw(f); sizes=sizes or [110]*len(lines)
    tot=sum(int(s*1.2) for s in sizes); y=(1920-tot)/2
    for t,s in zip(lines,sizes): text_c(dr,(0,1080),y,t,F(s),fg); y+=int(s*1.2)
    f.save(f"{fr}/{i:02d}.png")
frame_text(0,["YOUR SENSE OF","HUMOUR,","PRINTED."],sizes=[96,120,120])
caps=["1,599 EGP • HOODIE","1,499 EGP • SWEATSHIRT"]
for k,(b,d,s,c) in enumerate(PICKS[:8]):
    frame_photo(k+1,crop(b,d,s,c),"WEAR THE JOKE.",caps[s=="Sweatshirt"])
frame_text(9,["ANY 2 HOODIES","= FREE TEE"],sizes=[100,130])
frame_text(10,["FREE SHIPPING","CASH ON DELIVERY","MOCKERS.SHOP"],bg=K,fg=Y,sizes=[100,72,90])
durs=[1.4]+[1.1]*8+[1.6,2.2]
with open(f"{fr}/list.txt","w") as L:
    for i,dd in enumerate(durs): L.write(f"file '{i:02d}.png'\nduration {dd}\n")
    L.write(f"file '{len(durs)-1:02d}.png'\n")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",f"{fr}/list.txt","-vf","fps=30,format=yuv420p",
 "-c:v","libx264","-preset","medium","-crf","20","-movflags","+faststart",f"{O}/reel_design_is_the_joke.mp4"],check=True)
# ---------- 2) Carousel cards 1080x1350 ----------
for k,(b,d,s,c) in enumerate(PICKS[:6]+PICKS[8:10]):
    f=Image.new("RGB",(1080,1350),K); f.paste(crop(b,d,s,c,ratio=1.13).resize((1080,1220)),(0,0)); dr=ImageDraw.Draw(f)
    dr.rectangle((0,1220,1080,1350),fill=Y); text_c(dr,(0,1080),1250,("HOODIE 1,599" if s=="Hoodie" else "SWEATSHIRT 1,499")+" • FREE SHIPPING",F(50),K)
    f.save(f"{O}/card_{k+1:02d}_{d}_{s}.jpg",quality=92)
# ---------- 3) Bundle statics (4:5 and 9:16) ----------
for size,name in [((1080,1350),"bundle_4x5.jpg"),((1080,1920),"bundle_9x16.jpg")]:
    Wd,Ht=size; f=Image.new("RGB",size,Y); dr=ImageDraw.Draw(f); y0=70 if Ht==1350 else 260
    text_c(dr,(0,Wd),y0,"ANY 2 HOODIES",F(104),K); text_c(dr,(0,Wd),y0+125,"OR SWEATSHIRTS",F(84),K)
    ph=625 if Ht==1350 else 820; pw=500
    a=crop("b4","old-people","Hoodie","Black",ratio=ph/pw).resize((pw,ph)); bimg=crop("b3","the-nicest-asshole","Sweatshirt","DarkBlue",ratio=ph/pw).resize((pw,ph))
    py=y0+260; f.paste(a,(30,py)); f.paste(bimg,(550,py))
    dr.rectangle((0,py+ph,Wd,py+ph+260),fill=K)
    text_c(dr,(0,Wd),py+ph+30,"+ A TEE OF YOUR CHOICE: FREE",F(58),Y); text_c(dr,(0,Wd),py+ph+120,"+ SHIPPING: FREE",F(58),W)
    text_c(dr,(0,Wd),py+ph+285,"Cash on delivery • mockers.shop",F(44,"Bold"),K)
    f.save(f"{O}/{name}",quality=92)
print(sorted(os.listdir(O)))
