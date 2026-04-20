"""
Construye prompts optimizados por provider según Music Prompting Guide.
Regla: Genre first → Mood/energy → Instruments (específicos) → Tempo → Structure

PIVOT: 100% Melodic Techno & Dark Electronic — el nicho que genera tracción real.
Sub-géneros cubiertos: Melodic Techno (Afterlife), Dark Progressive, Peak Time,
Industrial Techno, Hypnotic Techno, Acid Techno, Deep Techno, Progressive House,
High-Tech Minimal (Boris Brejcha style), y Organic House/Downtempo.
"""

PROVIDER_PROMPT_TEMPLATES = {
    "lyria": {
        "instrumental": (
            "{genre} instrumental, {mood}, featuring {instruments}. "
            "{bpm} BPM, {key}. "
            "[0:00] Intro - {intro_desc} "
            "[0:30] Main theme - {main_desc} "
            "[1:15] Build - energy rising, tension building "
            "[1:45] Climax - full energy peak "
            "[2:30] Outro - resolves with echoing delays. "
            "Production: {production_quality}. "
            "No drums intro, clean mix, 44.1kHz stereo."
        ),
        "with_vocals": (
            "{genre} track, {mood}, {vocal_style} vocals. "
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

# ═══════════════════════════════════════════════════════════════════
# MELODIC TECHNO & DARK ELECTRONIC — 14 Sub-géneros
# Inspirado en: Anyma, Tale of Us, ARTBAT, Boris Brejcha,
# Amelie Lens, Charlotte de Witte, Colyn, Stephan Bodzin
# ═══════════════════════════════════════════════════════════════════

NICHE_PARAMS = {
    # ──────────────────────────────────────────────
    # 1. MELODIC TECHNO (Afterlife / ARTY style)
    # ──────────────────────────────────────────────
    "melodic techno afterlife style": {
        "genre": "melodic techno",
        "mood": "dark, hypnotic, cinematic, emotional",
        "instruments": "deep analog synth bassline, lush reverb pads, arpeggiated synthesizer, "
                       "ethereal vocal chops, driving kick drum, crisp hi-hats, layered claps",
        "bpm": 124,
        "key": "A minor",
        "production_quality": "Afterlife Records aesthetic, wide stereo field, deep sub-bass, "
                              "immersive reverb, cinematic breakdown, festival-ready drop",
        "intro_desc": "atmospheric pad wash with distant vocal texture fading in",
        "main_desc": "driving kick enters with hypnotic bassline and arpeggiated synth melody",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 2. DARK MELODIC TECHNO
    # ──────────────────────────────────────────────
    "dark melodic techno": {
        "genre": "dark melodic techno",
        "mood": "dark, intense, brooding, mysterious",
        "instruments": "distorted analog bass, dark pad layers, metallic percussion hits, "
                       "glitchy vocal samples, pounding kick drum, sharp snare, industrial textures",
        "bpm": 128,
        "key": "D minor",
        "production_quality": "underground warehouse aesthetic, heavy compression, dark atmosphere, "
                              "industrial edge, relentless groove, rumbling sub frequencies",
        "intro_desc": "sinister pad drone with metallic textures building slowly",
        "main_desc": "pounding kick with distorted bassline and dark synth stabs",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 3. PROGRESSIVE HOUSE / TECHNO
    # ──────────────────────────────────────────────
    "progressive techno": {
        "genre": "progressive techno",
        "mood": "uplifting, emotional, euphoric, driving",
        "instruments": "plucked synth melody, warm analog pads, rolling bassline, "
                       "shimmering arpeggios, tight kick drum, open hi-hats, tribal percussion",
        "bpm": 122,
        "key": "F minor",
        "production_quality": "polished, festival-grade, wide panoramic mix, emotional build-ups, "
                              "euphoric drops, Stephan Bodzin inspired melodicism",
        "intro_desc": "warm filtered pad rising with gentle percussion",
        "main_desc": "emotional pluck melody over driving bassline and progressive build",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 4. PEAK TIME TECHNO
    # ──────────────────────────────────────────────
    "peak time techno": {
        "genre": "peak time techno",
        "mood": "aggressive, powerful, relentless, explosive",
        "instruments": "massive distorted kick, acid 303 bassline, industrial stab synths, "
                       "crash cymbals, fast hi-hat rolls, heavy reverb claps, noise sweeps",
        "bpm": 135,
        "key": "E minor",
        "production_quality": "maximal energy, Amelie Lens / Charlotte de Witte style, "
                              "crushing kicks, warehouse rave sound, face-melting drops",
        "intro_desc": "rising noise sweep with industrial percussion building tension",
        "main_desc": "absolutely crushing kick drops with acid bassline and stabbing synths",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 5. HYPNOTIC TECHNO
    # ──────────────────────────────────────────────
    "hypnotic techno": {
        "genre": "hypnotic techno",
        "mood": "trance-inducing, mesmerizing, deep, meditative",
        "instruments": "repetitive modular synth patterns, deep sub kick, minimal hi-hats, "
                       "evolving filter sweeps, granular textures, subtle delays, drone bass",
        "bpm": 130,
        "key": "G minor",
        "production_quality": "Berlin underground aesthetic, Berghain sound, minimal but deep, "
                              "hypnotic repetition, subtle evolution over time, immersive",
        "intro_desc": "single modular loop fading in with subtle filter movement",
        "main_desc": "deep kick with hypnotic repeating pattern that evolves through filtering",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 6. INDUSTRIAL TECHNO
    # ──────────────────────────────────────────────
    "industrial techno": {
        "genre": "industrial techno",
        "mood": "dark, aggressive, mechanical, dystopian",
        "instruments": "distorted 909 kick, metallic clangs, factory noise samples, "
                       "harsh synth leads, heavy reverb snares, grinding bass, chains and impacts",
        "bpm": 138,
        "key": "C minor",
        "production_quality": "raw, abrasive, NØIS aesthetic, Perc / Ansome inspired, "
                              "smashed transients, brutal compression, no mercy",
        "intro_desc": "factory machinery sounds with distant pounding kick approaching",
        "main_desc": "brutal distorted kick with metallic hits and grinding bass assault",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 7. HIGH-TECH MINIMAL (Boris Brejcha style)
    # ──────────────────────────────────────────────
    "high tech minimal techno": {
        "genre": "high-tech minimal techno",
        "mood": "quirky, playful yet dark, intricate, groovy",
        "instruments": "plucky staccato synth lines, tight 808 kick, crisp claps, "
                       "bouncy bassline, filtered vocal cuts, playful arpeggios, subtle acid line",
        "bpm": 126,
        "key": "B minor",
        "production_quality": "Boris Brejcha signature style, playful but dark, intricate rhythms, "
                              "surgical precision mixing, groovy and hypnotic at the same time",
        "intro_desc": "quirky staccato synth pattern with bouncy groove",
        "main_desc": "driving groove with playful pluck melodies weaving over tight kick pattern",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 8. ACID TECHNO
    # ──────────────────────────────────────────────
    "acid techno": {
        "genre": "acid techno",
        "mood": "psychedelic, intense, raw, hypnotic",
        "instruments": "Roland TB-303 acid bassline, distorted 909 kick, resonant filter sweeps, "
                       "squelchy lead synth, crisp open hats, reverb snare, detuned stabs",
        "bpm": 133,
        "key": "F# minor",
        "production_quality": "acid rave aesthetic, heavy 303 resonance, squelchy filters, "
                              "raw energy, psychedelic textures, retro-futuristic",
        "intro_desc": "303 acid line filtering in slowly with building resonance",
        "main_desc": "full acid assault with squelchy bassline and pounding kick",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 9. DEEP TECHNO
    # ──────────────────────────────────────────────
    "deep techno": {
        "genre": "deep techno",
        "mood": "introspective, deep, warm, cerebral",
        "instruments": "warm deep bass synth, dub chord stabs, shuffled hi-hats, "
                       "deep kick with long tail, ethereal pad layers, subtle delay echoes",
        "bpm": 120,
        "key": "Eb minor",
        "production_quality": "deep and warm, dub-influenced, subtle groove, cerebral atmosphere, "
                              "late night club sound, introspective and immersive",
        "intro_desc": "deep distant pad with dub echo creating space",
        "main_desc": "warm deep kick enters with shuffled groove and dub stabs",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 10. MELODIC HOUSE & TECHNO (Anjunadeep vibes)
    # ──────────────────────────────────────────────
    "melodic house and techno": {
        "genre": "melodic house and techno",
        "mood": "dreamy, euphoric, emotional, uplifting",
        "instruments": "lush evolving synth pads, plucked melodic synth, warm sub bass, "
                       "soft kick, crisp shakers, piano chords, breathy vocal textures",
        "bpm": 121,
        "key": "Ab minor",
        "production_quality": "Anjunadeep / Lane 8 aesthetic, warm and lush, emotional depth, "
                              "sunset vibes, crystalline highs, deep warmth",
        "intro_desc": "breathy vocal texture over warm pad creating dreamscape",
        "main_desc": "emotional pluck melody rising over warm bass and soft driving kick",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 11. ORGANIC HOUSE / DOWNTEMPO ELECTRONICA
    # ──────────────────────────────────────────────
    "organic house electronica": {
        "genre": "organic house downtempo",
        "mood": "warm, natural, groovy, sensual",
        "instruments": "marimba, kalimba, organic percussion, deep warm bass, "
                       "tabla, shaker loops, world instrument textures, flute",
        "bpm": 115,
        "key": "D minor",
        "production_quality": "All Day I Dream aesthetic, organic textures, bohemian groove, "
                              "desert sunset vibes, natural instrument fusion with electronic bass",
        "intro_desc": "distant marimba pattern with organic percussion fading in",
        "main_desc": "groovy organic beat with kalimba melody and warm deep bass",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 12. TRANCE TECHNO (Artbat / Anyma crossover)
    # ──────────────────────────────────────────────
    "trance techno crossover": {
        "genre": "trance techno",
        "mood": "euphoric, powerful, transcendent, emotional",
        "instruments": "soaring trance lead synth, driving techno kick, epic pad layers, "
                       "rolling bass, breakdown piano, crash build-ups, vocal chants",
        "bpm": 132,
        "key": "C minor",
        "production_quality": "ARTBAT / Anyma crossover, massive festival drops, emotional trance "
                              "melodies over techno foundation, euphoric and transcendent",
        "intro_desc": "epic pad swell with distant trance lead hint",
        "main_desc": "soaring lead synth melody explodes over crushing techno kick and bass",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 13. DARK PROGRESSIVE (Tale of Us darker side)
    # ──────────────────────────────────────────────
    "dark progressive": {
        "genre": "dark progressive techno",
        "mood": "dark, atmospheric, slow-burning, cinematic",
        "instruments": "dark modular bass, cinematic string samples, tribal percussion, "
                       "ominous vocal textures, rumbling sub, delayed plucks, tension risers",
        "bpm": 123,
        "key": "Bb minor",
        "production_quality": "Tale of Us darker aesthetic, cinematic tension, slow-burning evolution, "
                              "dark and atmospheric, movie soundtrack meets underground club",
        "intro_desc": "ominous drone with distant cinematic strings creating tension",
        "main_desc": "dark modular bass grooves with tribal percussion and atmospheric textures",
        "has_vocals": False,
    },

    # ──────────────────────────────────────────────
    # 14. CYBERPUNK ELECTRONIC (el estilo Arcadia Music)
    # ──────────────────────────────────────────────
    "cyberpunk electronic": {
        "genre": "cyberpunk electronic techno",
        "mood": "futuristic, dark, neon-soaked, aggressive, cinematic",
        "instruments": "distorted glitch bass, cyberpunk synth leads, industrial kicks, "
                       "digital artifacts, neon arpeggiators, granular vocal processing, "
                       "heavy sidechain compression, bit-crushed textures",
        "bpm": 130,
        "key": "A minor",
        "production_quality": "Blade Runner meets underground rave, neon-noir aesthetic, "
                              "futuristic and aggressive, cyberpunk city soundscape, "
                              "heavy processing, dark and electrifying",
        "intro_desc": "digital static and glitch textures creating dystopian atmosphere",
        "main_desc": "massive distorted bass with neon synth leads and industrial rhythms",
        "has_vocals": False,
    },
}


def build_prompt(niche: str, provider: str, track_type: str = "instrumental") -> dict:
    """
    Construye prompt optimizado según provider y tipo de track.
    Retorna dict con prompt_full (pro) y prompt_clip (30s test).
    """
    params = NICHE_PARAMS.get(niche, {
        "genre": niche, "mood": "dark, driving, hypnotic",
        "instruments": "analog synths, driving kick, deep bass, atmospheric pads",
        "bpm": 126, "key": "A minor",
        "production_quality": "professional electronic music production, club-ready",
        "intro_desc": "atmospheric synth building tension",
        "main_desc": "driving kick with melodic synth layers",
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
