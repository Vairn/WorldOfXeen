## Porting World of Xeen (ScummVM) to Amiga/ACE in C

This document describes a detailed plan to port the ScummVM C++ Xeen engine to the Amiga using ACE and C. It covers architecture mapping, subsystem plans, data formats, milestones, and risks.

### Goals and Scope
- **Primary goal**: Run World of Xeen (Clouds + Darkside) gameplay on Amiga via ACE in C, preserving core mechanics, UI, and content.
- **Reuse**: Xeen CC archives, palettes, sprites, maps, scripts; preconvert assets when beneficial.
- **Integrate with ACE**: Input, graphics, audio, state manager.
- **Parity targets**: Map navigation, UI, interactions, inventory/party, scripts/events, combat, saves/loads.
- **Out of scope for v1**: ScummVM launcher/metaengine, TTS, ScummVM debugger GUI, advanced config manager.

### High-Level Architecture Mapping
The ScummVM engine core (`MM::Xeen::XeenEngine`) orchestrates subsystems and loops:
- Engine setup → `initialize()` creates: Files, Resources, Screen, Interface, Map, Party, Spells, Combat, Scripts, Saves, Windows, Sound, Events.
- Outer loop → `outerGameLoop()` switches Startup/Menu/Play states.
- Inner loop → `gameLoop()` handles events, treasure, input/UI perform, death/exit.

ACE/C mapping:
- Replace `XeenEngine` with `xeen_engine_t` and C functions: `xeen_engine_init`, `xeen_engine_run`, `xeen_engine_outer_loop`, `xeen_engine_game_loop`, `xeen_engine_play`, `xeen_engine_play_game`.
- Use ACE `tState` for startup/menu/game states. Your existing entry point in `src/main.c` pushes `g_sStateGame`.

### Target Platform Decisions
- **Graphics**: 320x200, 256 colors ideal (AGA). For OCS/ECS (32/64 colors), prequantize assets and use remap tables.
- **Memory**: Aim for 2MB Chip + Fast RAM. Stream assets, cache aggressively.
- **Timing**: VBlank-synced palette fades and buffer swaps.

### Amiga Targets and Memory/Performance Budgets
- Primary target: Stock A1200 (AGA, 2 MB Chip, no Fast). All runtime systems must fit and perform acceptably without Fast RAM.
- Optional enhancement: If Fast RAM is present, prefer allocating caches/work buffers from Fast to gain ~20–40% headroom automatically.

Memory budget on stock A1200 (guidelines):
- Screen pages: two 320×200×8-bitplane pages ≈ 64 KB each → ~128 KB total.
- Background saves: limit to 1–2 slots (64–128 KB), configurable.
- UI/sprite caches: cap decoded sprite memory to ~600–800 KB; load per area; purge on map change.
- Audio buffers: ≤128 KB (tunable).
- Working data (party/map/state): ~200–300 KB typical.

Performance notes (no Fast):
- Use blitter for sprite/UI copies; favor fewer large blits over many small ones.
- Copper for palette fades where possible; otherwise tiny per-frame steps.
- Avoid runtime chunky→planar conversion; all assets preconverted to bitplanes.
- Target ~25–30 Hz UI; ~15–20 Hz scene redraws are acceptable for a step RPG.

### Directory and Module Plan
- `src/engine/`: `xeen_engine.c/.h`, `game_states.c/.h`
- `src/gfx/`: `screen.c/.h`, `window.c/.h`, `sprites.c/.h`, `font.c/.h`
- `src/io/`: `files.c/.h`, `cc_archive.c/.h`, `serializer.c/.h`, `saves.c/.h`
- `src/game/`: `interface.c/.h`, `map.c/.h`, `party.c/.h`, `character.c/.h`, `items.c/.h`, `events.c/.h`, `scripts.c/.h`, `combat.c/.h`, `spells.c/.h`, `resources.c/.h`, `sound.c/.h`
- `src/compat/`: `common_types.h`, `rect.h`, `point.h`, `util.c/.h`
- `tools/` (host-side): asset preconverters (palettes, sprites, backgrounds)

### C++ Feature Replacement Strategy
- **Classes/Inheritance** → C `struct` with function sets; optional vtables for polymorphism.
- **Common::Array/String/Rect/Point** → custom C: dynamic/static arrays, `const char *`, simple structs.
- **Streams/Serializer** → explicit LE read/write functions wrapping ACE or stdio.
- **ManagedSurface/Graphics::Screen** → ACE buffers or chunky offscreen buffers with blits/fades.
- **ConfMan/MetaEngine/TTS** → constants or project-local config; omit TTS/metaengine.

### Resource and File Formats
- **CC archives**: Implement read-only index + member read by id/path, mirroring `mm/shared/xeen/cc_archive.*` behavior.
- **Backgrounds `.raw`**: Load into screen/page buffer; confirm pixel layout (likely 8-bit chunky in CC).
- **Palettes `.pal`**: 256×RGB; map to Amiga palette; pre-reduce for OCS/ECS.
- **Sprites**: Port `SpriteResource` decode/draw; or preconvert to blitter-friendly format.
- **Maps**: 16×16 maze, wall layers, flags, monsters/objects, animations.
- **Saves**: Implement serializer-compatible structure; or define a simpler LE format preserving all dynamic state.

### Subsystem-by-Subsystem Mapping
- **Engine**: Create, run, outer loop, inner loop; modes and game modes as enums.
- **Files**: `files_setup`, `files_set_game_cc`, `files_load/save`, `save_archive_replace_entry`.
- **Resources**: Tables/strings/colors/indices; initially minimal to boot, then full set.
- **Screen**: Pages, palettes, fades, background load, merges, save/restore.
- **Windows**: Window stack, dirty rects, fill/frame, text, draw lists; bitmap fonts.
- **Interface**: Setup, startup, main icons, perform (input loop), time step, movement, falling, obscurity, combat UI.
- **Party/Character/Items**: Party time/gold/gems/flags, roster, active party, inventory management, HP/SP bars.
- **Map/Maze**: Load, `cellFlagLookup`, `mazeLookup`, surrounding maps, sky/ground/tile rendering, monster/object lists, animation info.
- **Scripts/Events**: Trigger detection; process events to return mode transitions.
- **Combat/Spells**: Initial stubs; then turn logic, damage/resistances, UI; core spells.
- **Audio**: ACE SFX first; music later as feasible.

### ACE Integration
- Entry point is already set (`genericCreate/Process/Destroy` and `g_sStateGame`). Implement additional `tState`s: `g_sStateLogo`, `g_sStateIntro`, `g_sStateTitle`.
- Input mapping: ACE key/mouse → engine actions in `interface_perform`.
- Video: Double buffering; palette updates on VBlank; avoid tearing.

### Minimal Viable Bring-up (Phase 1)
Target: Boot, load `back.raw` + `mm4.pal`, fade in, draw UI frame.
1) Implement `cc_archive` read-only open/index/read.
2) Implement `screen_loadPalette`, `screen_loadBackground`, `screen_fadeIn/out`.
3) Implement `resources_init` minimal constants.
4) Implement `interface_setup/startup/mainIconsPrint` as stubs that draw borders/text.
5) Wire into `g_sStateGame` state loop to call `xeen_engine_play_game`.

### Detailed Porting Steps and Milestones
Milestone 0: Project scaffolding (1–2 days)
- Create module skeletons/headers per layout; update `CMakeLists.txt`.
- Add `compat/` primitives (rect/point/endian/dynarray).

Milestone 1: Asset tools (preconversion) (5–8 days)
- Implement host tools: `xeencc_unpack`, `xeen_pal_convert`, `xeen_bg_convert`, `xeen_spr_convert`, `xeen_pack_assets`.
- Document usage and legal notes; generate `manifest.json` and CRCs.
- Acceptance: Produce `amiga_assets.xpa` from original data; `xeen_verify_assets` passes.

Milestone 2: File/Resource I/O (3–5 days)
- Runtime reader for `.xpa` archive: open, index, read by path/id.
- Palette/background loaders consuming preconverted outputs; display background on A1200.
- Acceptance: Boot shows converted `back.bpl` with `mm4_aga.pal` and fades in.

Milestone 3: Screen/Window/Font (3–5 days)
- Double buffer, palette fades; basic windowing and bitmap font text.
- Draw UI frame; test text output.
- Acceptance: UI frame rendered; text legible; no flicker/tearing.

Milestone 4: Resources tables (4–6 days)
- Port/inline essential tables (strings, colors, indices) used by UI and map.
- Load UI sprites for borders/icons.
- Acceptance: Main icons and borders visible; color constants applied.

Milestone 5: Interface core (4–7 days)
- Implement `interface_setup/startup/mainIconsPrint/perform` with input polling.
- Render 3D scene placeholder; cursor; button container stubs.
- Acceptance: Navigate UI; keypresses update focus; stable for 5 minutes idle.

Milestone 6: Map core (7–10 days)
- Port `MazeData`, `MonsterData`, `MonsterObjectData`, `AnimationInfo` structs/loaders.
- Implement `map_load`, `cellFlagLookup`, `mazeLookup`, sky/ground/tile rendering.
- Party movement (N/E/S/W); redraw loop.
- Acceptance: Move around a test map; sky/ground/tile layers render; edge crossing loads adjacent map.

Milestone 7: Party/Inventory (5–8 days)
- Party dynamic state, time progression, light handling, treasure, packs.
- Character essentials: HP/SP bars, names, face sprites draw.
- Acceptance: Party stats visible and update with time; treasure reflected in inventory/gold.

Milestone 8: Events/Scripts (7–10 days)
- Event triggers + subset of script actions; dialogs windows & text pages.
- Acceptance: Stepping on an event triggers dialog; at least 3 actions (text, teleporter, treasure) work.

Milestone 9: Saves/Loads (4–6 days)
- Serializer + save archive; manual save/load; autosave optional.
- LE correctness on big-endian 68k.
- Acceptance: Save, reboot, load restores position, party stats, flags.

Milestone 10: Combat/Spells (10–15 days)
- Combat UI, turn logic, monster sprite loads/animations, damage calculations.
- Core spell effects and resistances.
- Acceptance: Complete a simple encounter; damage/resists match tables.

Milestone 11: Audio (4–7 days)
- ACE SFX playback; optional music support.
- Acceptance: SFX play without stutter; mixer settings adjustable.

Milestone 12: Polish/Performance/OCS-ECS (7–14 days)
- Optimize blits/sprite decode; caching.
- Preconversion pipeline for limited color modes.
- Acceptance: Stable 25–30 Hz UI on A1200; memory fits 2 MB Chip; optional OCS/ECS asset profile builds.

### Data Preconversion Strategy (Recommended)
- Host tools convert:
  - Palettes: quantize for OCS/ECS; produce remap tables.
  - Sprites/backgrounds: to blitter/bitplane-ready buffers; RLE optimized.
  - Optional: repack into simplified archive with offsets.
- Benefits: faster loads, simpler runtime, better performance on 68k.

Preconversion toolchain and workflow:
- Location: `tools/` directory with CLI utilities (portable C; Python acceptable for prototypes).
- Inputs: User-provided original game data (commercial). We do not ship assets.
- Outputs: Preconverted assets in an Amiga-friendly archive (or loose files) consumed by the engine.
- Legal: Provide tools and docs only. Users must point tools at their own legally obtained data.

Tools to provide:
- `xeencc_unpack`: Index/extract CC archives to a workspace folder.
- `xeen_pal_convert`: Convert `.pal` to AGA palette binary; optional OCS/ECS quantization + remap tables.
- `xeen_bg_convert`: Convert backgrounds to 8 bitplanes (aligned for blitter), optional RLE.
- `xeen_spr_convert`: Convert sprite resources to bitplanes + metadata (frame rects, flags, offsets), optional per-scanline RLE.
- `xeen_pack_assets`: Repack converted assets into a simple indexable archive with offsets and checksums.
- `xeen_verify_assets`: Verify presence/CRC/version of required entries.

Suggested CLI:
- `xeencc_unpack --input <path_to_cc> --out out/cc_unpacked`
- `xeen_pal_convert --in out/cc_unpacked/mm4.pal --aga --out out/pal/mm4_aga.pal`
- `xeen_bg_convert --in out/cc_unpacked/back.raw --out out/bg/back.bpl`
- `xeen_spr_convert --in out/cc_unpacked/sprites/*.dat --out out/spr/`
- `xeen_pack_assets --root out --out amiga_assets.xpa`
- `xeen_verify_assets --archive amiga_assets.xpa`

Archive format (`.xpa`, example):
- Header: magic, version, entry count.
- TOC: name hash + offset + size + CRC32.
- Data: concatenated payloads. Little-endian on disk; verified via CRC.

Reproducibility:
- Deterministic outputs (stable sort orders, fixed quantization seeds).
- Emit a manifest (`manifest.json`) with file hashes and tool versions.

### Type and API Shims
- `Rect { int16 x,y,w,h; }`, `Point { int16 x,y; }`.
- Strings as `const char *` for resources; dynamic strings via small string buffer utility.
- Arrays: fixed-size where possible; small `dynarray` helper for variable lists.
- Endian helpers for LE <-> 68k.

### Save/Serializer Plan
- `serializer_t` with mode (read/write), version, bytes_synced, and LE helpers.
- Per-struct `synchronize(serializer_t*)` functions mirroring ScummVM structure layout.
- Cover: Party, Map dynamic parts, Blacksmith wares, Flags, Roster/Active party, Timers.

### Error Handling and Logging
- Use ACE log manager or serial prints.
- No exceptions; return error codes; centralized error macros.

### Performance Considerations
- Preallocate buffers (pages, caches); avoid heap churn.
- Lazy-load sprites; optional LRU cache.
- Fixed-point math where heavy; avoid divisions inside inner loops.
- Palette fades via copper lists if available; else small per-frame steps.

### Licensing
- ScummVM code is GPL; derived work must remain GPL-compatible. If clean-room is required, reimplement algorithms from format specs and behavior descriptions instead of copying code.

### Risks and Mitigations
- 256-color assets on OCS/ECS: target AGA first; prequantize for ECS; UI color tuning.
- Sprite/format complexity: start on host tools for decode validation; build test corpus.
- Big-endian pitfalls: always use LE helpers and explicit packing; avoid `memcpy` of packed structs.
- Performance: preconvert heavy assets; profile hot paths; cache smartly.

### File-to-Module Mapping Examples
- `mm/xeen/xeen.(h|cpp)` → `src/engine/xeen_engine.c/.h`, `src/engine/game_states.c/.h`
- `mm/xeen/screen.(h|cpp)` → `src/gfx/screen.c/.h`
- `mm/xeen/window.(h|cpp)` → `src/gfx/window.c/.h`
- `mm/xeen/interface.(h|cpp)` → `src/game/interface.c/.h`
- `mm/xeen/map.(h|cpp)` → `src/game/map.c/.h`
- `mm/xeen/party.(h|cpp)` → `src/game/party.c/.h`
- `mm/shared/xeen/cc_archive.(h|cpp)` → `src/io/cc_archive.c/.h`
- `mm/xeen/resources.(h|cpp)` → `src/game/resources.c/.h`

### Testing Strategy
- Host-side unit tests for loaders: CC archives, palettes, backgrounds, sprites, maps.
- Hardware smoke test: boot, fade in, draw background + UI frame.
- Incremental gameplay checks per milestone: movement, dialogs/events, save/load, a basic combat.

### Timeline (Rough)
- M0–M2: 1–2 weeks
- M3–M5: 2–3 weeks
- M6–M8: 2–3 weeks
- M9–M11: 3–4 weeks
Total: ~8–12 weeks depending on fidelity, preconversion, and hardware targets.

### Immediate Next Actions
- Choose target: AGA-first vs. OCS/ECS compatibility via preconversion.
- Implement `screen.c` with palette/background load + fades; show `back.raw` + `mm4.pal`.
- Implement minimal `cc_archive` read to access those assets.
- Stub `interface_*` to draw borders/text.

### Existing Entry Points
- `src/main.c`: sets up ACE managers and pushes `g_sStateGame` (`keyCreate`, `stateManagerCreate`, `stateProcess`).
- `include/game.h`: declares `g_sStateGame` and other states; integrate new states as needed.


