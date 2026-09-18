from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Request(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    language: Literal['Hindi', 'Hinglish', 'English'] = 'Hindi'
    aspect: Literal['16:9'] = '16:9'
    mode: Literal['demo', 'live'] = 'live'
    audio_mode: Literal['elevenlabs'] = 'elevenlabs'
    @model_validator(mode='after')
    def clean(self):
        self.title = self.title.strip()
        if len(self.title) < 2 or any(ord(c)<32 for c in self.title):
            raise ValueError('Enter a title with at least two printable characters')
        return self

class Line(BaseModel):
    speaker: str
    text: str = Field(min_length=1, max_length=400)
    emotion: str
class Story(BaseModel):
    hook: str
    entity: str
    # The course adaptation is one locked spoken beat per act.
    lines: list[Line] = Field(min_length=6, max_length=6)
class Character(BaseModel):
    tag: str = Field(pattern=r'^@CHAR-\d{2}-[A-Z0-9-]+$')
    name: str
    look: str
    voice: Literal['Charon', 'Kore', 'Puck', 'Fenrir', 'Aoede']
    performance: str
    reference_prompt: str
class Cast(BaseModel):
    characters: list[Character] = Field(min_length=1, max_length=3)
class Background(BaseModel):
    tag: str = Field(pattern=r'^#BGD-\d{2}-[A-Z0-9-]+$')
    location: str
    prompt: str
    angles: list[str] = Field(min_length=2, max_length=3)
class Locations(BaseModel):
    backgrounds: list[Background] = Field(min_length=1, max_length=3)
class Scene(BaseModel):
    title: str
    character_tags: list[str] = Field(max_length=3)
    background_tag: str
    background_angle: int = Field(default=1, ge=1, le=3)
    still_prompt: str
    animation_prompt: str
    physics_effects: str = 'Restrained scene-specific movement; preserve geometry.'
    audio_prompt: str = 'Restrained location ambience, no music.'
    sound: Literal['wind', 'heartbeat', 'sting', 'none']
class Scenes(BaseModel):
    scenes: list[Scene] = Field(min_length=6, max_length=6)
class Publishing(BaseModel):
    titles: list[str] = Field(min_length=10, max_length=10)
    description: str
    hashtags: list[str] = Field(min_length=12, max_length=15)
    tags: str = Field(max_length=500)
    thumbnail_prompts: list[str] = Field(min_length=10, max_length=10)
    @model_validator(mode='after')
    def validate_package(self):
        if any(len(t)>100 for t in self.titles): raise ValueError('Titles must be under 100 characters')
        if len(self.description.split()) < 350: raise ValueError('Description needs at least 350 words')
        return self

def validate_links(story, cast, locations, scenes):
    names = {c['name']:c['tag'] for c in cast['characters']}
    tags = set(names.values())
    bgs = {b['tag'] for b in locations['backgrounds']}
    if len(tags)!=len(cast['characters']) or len(names)!=len(tags): raise ValueError('Duplicate character')
    if len(bgs)!=len(locations['backgrounds']): raise ValueError('Duplicate background')
    if len(story['lines']) != 6 or len(scenes['scenes']) != 6:
        raise ValueError('The locked course adaptation must contain exactly six acts/scenes.')
    for index, (line, scene) in enumerate(zip(story['lines'], scenes['scenes'], strict=True), 1):
        if not scene['still_prompt'] or scene['still_prompt'].lower().startswith(('demo card:', 'placeholder')):
            raise ValueError(f'Scene {index} contains a placeholder still prompt')
        if not scene['animation_prompt'] or scene['animation_prompt'].lower().startswith(('demo card:', 'placeholder')):
            raise ValueError(f'Scene {index} contains a placeholder animation prompt')
        # A continuing shot may legitimately reuse its background and angle.
        if len(scene['character_tags']) != len(set(scene['character_tags'])):
            raise ValueError('Duplicate scene character tag')
        if scene['background_tag'] not in bgs or not set(scene['character_tags'])<=tags: raise ValueError('Unknown asset tag')
        background=next(b for b in locations['backgrounds'] if b['tag']==scene['background_tag'])
        if not 1 <= scene.get('background_angle',1)<=len(background['angles']): raise ValueError('Unknown background angle')
        if line['speaker'] != 'NARRATOR':
            if line['speaker'] not in names: raise ValueError('Unknown speaker')
            if names[line['speaker']] not in scene['character_tags']: raise ValueError('Speaker is missing from scene')

class VisualReview(BaseModel):
    consistent: bool
    issues: list[str]
    correction: str
