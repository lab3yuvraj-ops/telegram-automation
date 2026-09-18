"""Local-only helpers for the explicitly labeled demo mode."""
from PIL import Image, ImageDraw, ImageFont

def demo_image(path, title, number=0, aspect='16:9'):
    # Deliberately a typographic test card, never represented as generated footage.
    size=(1280,720) if aspect=='16:9' else (720,1280)
    im=Image.new('RGB',size,'#0b1117'); d=ImageDraw.Draw(im)
    try:
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',44)
        small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    except OSError: font=small=ImageFont.load_default()
    d.rectangle((40,40,size[0]-40,size[1]-40),outline='#314d4c',width=2)
    d.text((75,85),'NIGHTFALL / PIPELINE PREVIEW',font=small,fill='#b9ed86')
    d.text((75,size[1]//2-40),f'{number:02d}  /  {title[:24]}',font=font,fill='#f0f1eb')
    d.text((75,size[1]-125),'DEMO TEST CARD - NO AI FOOTAGE',font=small,fill='#829593')
    im.save(path)
