"""
Construye prompts optimizados por provider según Music Prompting Guide.
Regla: Genre first → Mood/energy → Instruments (específicos) → Tempo → Structure
"""

PROVIDER_PROMPT_TEMPLATES = {
    "lyria": {
        "instrumental": (
            "{genre} instrumental, {mood}, featuring {instruments}. "
            "{bpm} BPM, {key}. "
            "[0:00] Intro - {intro_desc} "
            "[0:30] Main theme - {main_desc} "
            "[1:15] Build - energy rising "
            "[1:45] Outro - resolves softly. "
            "Production: {production_quality}. "
            "No drums intro, clean mix, 44.1kHz stereo."
        ),
        "with_vocals": (
            "{genre} song, {mood}, {vocal_style} vocals. "
            "{bpm} BPM, key of {key}. "
            "[Verse] {verse_desc} "
            "[Chorus] {chorus_desc} "
            "[Bridge] {bridge_desc} "
            "Instruments: {instruments}. {production_quality}."
        )
    },
    "stable_audio": {
        "instrumental": (
            "{bpm} BPM {genre} track. "
            "{instruments}. "
            "{mood} mood. "
            "{production_quality}. "
            "Stereo, high quality, 44.1kHz."
        )
    },
    "musicgen": {
        "instrumental": (
            "{genre}, {mood}, {instruments}, "
            "{bpm} BPM, {production_quality}"
        )
    }
}

NICHE_PARAMS = {
    "lofi hip hop para estudiar": {
        "genre": "lo-fi hip hop",
        "mood": "calm, relaxed, focused",
        "instruments": "mellow Rhodes piano, soft boom bap drums, warm bass, vinyl crackle",
        "bpm": 75,
        "key": "F minor",
        "production_quality": "warm analog, lo-fi texture, slight saturation",
        "intro_desc": "soft piano chords with vinyl noise",
        "main_desc": "drums enter, lazy groove",
        "has_vocals": False,
    },
    "música épica cinematográfica para trailers": {
        "genre": "epic cinematic orchestral",
        "mood": "powerful, dramatic, triumphant",
        "instruments": "full orchestra: brass section, strings, choir, epic percussion, timpani",
        "bpm": 130,
        "key": "D minor",
        "production_quality": "polished, professional, wide stereo, Hans Zimmer-style",
        "intro_desc": "solo strings, tense",
        "main_desc": "brass and choir swell",
        "has_vocals": False,
    },
    "ambient relajante para meditar": {
        "genre": "ambient",
        "mood": "peaceful, ethereal, meditative",
        "instruments": "ethereal synth pads, soft piano, gentle nature textures, light bells",
        "bpm": 60,
        "key": "C major",
        "production_quality": "spacious, reverb-heavy, warm, smooth transitions",
        "intro_desc": "single pad fades in slowly",
        "main_desc": "layers build gently",
        "has_vocals": False,
    },
    "música de fondo para podcasts": {
        "genre": "corporate background music",
        "mood": "uplifting, professional, non-distracting",
        "instruments": "light acoustic guitar, subtle piano, soft percussion",
        "bpm": 100,
        "key": "G major",
        "production_quality": "clean, polished, mixed low for voice-over",
        "intro_desc": "gentle guitar arpeggios",
        "main_desc": "piano joins, steady groove",
        "has_vocals": False,
    },
    "chiptune 8-bit para videojuegos": {
        "genre": "chiptune 8-bit",
        "mood": "energetic, fun, retro",
        "instruments": "NES-style square waves, triangle bass, noise drum channel",
        "bpm": 150,
        "key": "A major",
        "production_quality": "crisp digital, authentic Game Boy aesthetic",
        "intro_desc": "arpeggiated fanfare",
        "main_desc": "driving melody loop",
        "has_vocals": False,
    },
    "jazz instrumental para trabajar": {
        "genre": "jazz",
        "mood": "relaxed, sophisticated, warm",
        "instruments": "upright bass walking line, brushed drums, Rhodes electric piano, muted trumpet",
        "bpm": 120,
        "key": "Bb major",
        "production_quality": "warm analog, room ambience, intimate feel",
        "intro_desc": "bass intro, 4 bars",
        "main_desc": "Rhodes comping, trumpet melody",
        "has_vocals": False,
    },
    "synthwave retro 80s": {
        "genre": "synthwave",
        "mood": "nostalgic, dreamy, cool",
        "instruments": "arpeggiated analog synths, gated reverb drums, warm bass synth, pad layers",
        "bpm": 110,
        "key": "E minor",
        "production_quality": "vintage 80s aesthetic, heavy reverb, neon-soaked",
        "intro_desc": "synth arpeggio alone",
        "main_desc": "drums enter, full synth layers",
        "has_vocals": False,
    },
    "música dramática para YouTube vlogs": {
        "genre": "dramatic vlog background music",
        "mood": "dramatic, intense, building",
        "instruments": "staccato strings, driving bass, modern electronic percussion, synth plucks",
        "bpm": 115,
        "key": "A minor",
        "production_quality": "modern, punchy, crisp highs",
        "intro_desc": "staccato strings build tension",
        "main_desc": "electronic beat drops, driving synth bass",
        "has_vocals": False,
    },
    "trap beats instrumentales": {
        "genre": "trap beat",
        "mood": "dark, aggressive, energetic",
        "instruments": "808 bass, fast hi-hats, minor piano melody, snare rolls",
        "bpm": 140,
        "key": "C minor",
        "production_quality": "heavy bass, clean 808s, modern hip hop production",
        "intro_desc": "dark piano melody",
        "main_desc": "808 bass drops, fast hi-hat groove",
        "has_vocals": False,
    },
    "música acústica para cafeterías": {
        "genre": "acoustic coffee shop music",
        "mood": "cozy, warm, inviting",
        "instruments": "fingerstyle acoustic guitar, upright bass, gentle brushes on snare",
        "bpm": 85,
        "key": "G major",
        "production_quality": "intimate, acoustic warmth, natural reverb",
        "intro_desc": "solo acoustic guitar melody",
        "main_desc": "bass and brushes join, gentle groove",
        "has_vocals": False,
    }
}


def build_prompt(niche: str, provider: str, track_type: str = "instrumental") -> dict:
    """
    Construye prompt optimizado según provider y tipo de track.
    Retorna dict con prompt_full (pro) y prompt_clip (30s test).
    """
    params = NICHE_PARAMS.get(niche, {
        "genre": niche, "mood": "neutral", 
        "instruments": "piano, strings",
        "bpm": 100, "key": "C major",
        "production_quality": "professional, high quality",
        "intro_desc": "soft intro", "main_desc": "main theme",
        "has_vocals": False,
    })
    
    template_key = "with_vocals" if params.get("has_vocals") else "instrumental"
    template = PROVIDER_PROMPT_TEMPLATES[provider].get(template_key)
    if not template:
        template = PROVIDER_PROMPT_TEMPLATES[provider]["instrumental"]
    
    prompt_full = template.format(**params)
    
    prompt_clip = (
        f"{params['genre']}, {params['mood']}, "
        f"{params['instruments']}, {params['bpm']} BPM. "
        f"30 second preview clip."
    )
    
    return {
        "prompt_full": prompt_full,
        "prompt_clip": prompt_clip,
        "params": params,
    }
