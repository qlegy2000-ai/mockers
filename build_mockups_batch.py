import sys, json, glob, os, statistics as stt
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,'/home/user/mockers')
from compose_v2 import compose
from measure_placement import landmarks, ratios, plausible, _lab
S=os.path.dirname(os.path.abspath(__file__)); os.chdir(S)
os.makedirs('art26c',exist_ok=True); os.makedirs('b4',exist_ok=True)
st=json.load(open('state26.json'))
PAGE={"diet-joke":20,"divers-evolution":22,"five-beers":29,"funny-how":30,"hope":34,"italien":42,"jomo":43,
 "led-zep":47,"middle-fingers":49,"millennials":(50,51),"moana-chicken":55,"must-be-ai":58,"nudism":66,"old-people":67,
 "reality-called":75,"rock-paper-liquor":77,"shit":81,"sorry-princess":82,"stoned":84,"telefreak":88,"tequla":89,
 "try-me":93,"uncle-wes":94,"wtf":99,"into-resting":41,"veganism":96,"i-choose-violance":None,"im-not-judgemantal":45}
GC={"Black":"#121212","Offwhite":"#fffef4","Purple":"#3a2440","IronGrey":"#2b2b2b","AegeanBlue":"#0d3241",
    "DarkGreen":"#152A18","DarkBlue":"#011124","BeetrootPurple":"#2E0512"}
def clean(n):
    out=f'art26c/p{n:03d}.png'
    if os.path.exists(out): return out
    im=Image.open(f'art26/p{n:03d}.png').convert('RGBA'); a=np.array(im).astype(float)
    al=a[...,3]
    if (al[[0,-1],:].mean()>200) and (al[:,[0,-1]].mean()>200):   # opaque page background -> remove border-connected bg colour
        lab=_lab(a[...,:3]); bg=np.median(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]]),0)
        dist=np.linalg.norm(lab-bg,axis=-1); near=dist<12
        lbl,_=ndi.label(dist<40); edge=set(np.unique(np.concatenate([lbl[0],lbl[-1],lbl[:,0],lbl[:,-1]])))-{0}
        zone=np.isin(lbl,list(edge))                     # bg plus its anti-aliased fringe
        alpha=np.where(zone,np.clip((dist-12)/28,0,1),1.0)
        bgrgb=np.median(np.concatenate([a[0,:,:3],a[-1,:,:3],a[:,0,:3],a[:,-1,:3]]),0)
        safe=np.maximum(alpha,1e-3)[...,None]
        a[...,:3]=np.clip((a[...,:3]-(1-alpha[...,None])*bgrgb)/safe,0,255)   # un-mix bg colour from edges
        a[...,3]=al*alpha
    Image.fromarray(a.astype(np.uint8)).save(out); return out
def hex2lab(h): return _lab(np.array([[[int(h[i:i+2],16) for i in (1,3,5)]]],float))[0,0]
def lowcontrast(art,col):
    a=np.array(Image.open(art).convert('RGBA')).astype(float); m=a[...,3]>200
    if not m.any(): return 1
    L=_lab(a[...,:3][m])[:,0]; g=hex2lab(GC[col])[0]
    return float((np.abs(L-g)<(22 if col=="Offwhite" else 25)).mean())   # lightness contrast: catches yellow on Offwhite, dark red on dark
def aspect(art):
    im=Image.open(art); bb=im.split()[-1].point(lambda v:255 if v>20 else 0).getbbox(); return (bb[3]-bb[1])/(bb[2]-bb[0])
def refratios(d,style,asp):
    vals=[]
    for f in glob.glob(f'refs3/{d}-{style}-*.jpg'):
        try: r=ratios(landmarks(Image.open(f)))
        except Exception: r=None
        if plausible(r) and abs(r["aspect"]/asp-1)<0.3: vals.append(r)
    return vals
report={}
for h,o in sorted(st.items()):
    d,style=h.rsplit('-',1); style=style.capitalize()
    for col in [c.replace(' ','') for c in o["missing_on_sale"]]:
        if d=="veganism": report[f"{d}_{style}_{col}"]="SKIP owner rule: Veganism White/Offwhite only"; continue
        pg=PAGE.get(d)
        if d=="i-choose-violance": art="artfull/p18.png"
        elif pg is None: report[f"{d}_{style}_{col}"]="NO ART"; continue
        else:
            pg=(pg[1] if col=="Offwhite" else pg[0]) if isinstance(pg,tuple) else pg
            art=clean(pg)
        lc=lowcontrast(art,col); asp=aspect(art)
        key=f"{d}_{style}_{col}"
        if d=="try-me" and col!="Offwhite": report[key]="SKIP dark-red ink: Offwhite only"; continue
        force = d=="shit" and col!="Offwhite"   # owner already sells it on dark garments (blue logo, white outline)
        if lc>0.35 and not force: report[f"{d}_{style}_{col}"]=f"SKIP contrast {lc:.0%} of ink too close to garment"; continue
        own=refratios(d,style,asp); other=refratios(d,"Sweatshirt" if style=="Hoodie" else "Hoodie",asp)
        src=own or other
        if src: w=stt.median(r["w"] for r in src); top=stt.median(r["top"] for r in src); how=("own" if own else "other")+f"x{len(src)}"
        else: w=0.36; top=0.20; how="default"
        top=min(max(top,0.17),0.22)                      # lesson: start ~0.19-0.21 below neckline
        w=min(w,0.45,(0.075/asp)**0.5)                    # lesson: cap size
        compose(art,style,col,"models",f"b4/{d}_{style}_{col}.jpg",w,top)
        report[f"{d}_{style}_{col}"]=f"OK w={w:.3f} top={top:.3f} {how} lowc={lc:.0%}"
json.dump(report,open('b4_report.json','w'),indent=1)
for k,v in report.items(): print(f"{k:45} {v}")
