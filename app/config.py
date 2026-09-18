from pathlib import Path
from dotenv import load_dotenv
import os
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env.telegram')
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
STYLE = 'Cinematic 2D semi-realistic Indian horror illustration in the supplied visual tone: confident dark ink outlines, refined hand-drawn cel shading, expressive adult Indian human faces, natural anatomy, warm brown skin tones, and restrained realistic proportions. Use moody teal-blue night illumination, cyan fluorescent practical lights, rain-streaked glass, misty atmospheric depth, textured dark interiors, and selective warm skin highlights. Preserve canonical faces, hairstyles, clothing colors and distinguishing marks. No oversized heads, chibi bodies, distorted hands, extra characters, photorealism, 3D, CGI, text or watermarks. Compose horizontally in 16:9.'
