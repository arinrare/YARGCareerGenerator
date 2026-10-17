# YARG Career Builder

Build YARG **career** presets from your song library, outside the in-game editor.
Songs are referenced by **Song Tuple** (title, artist, charter, source) so the resulting career is portable/shareable.

## Files

- `settings.json` — all configuration (paths, visibility, difficulty, source selection, tiers).
- `sources.json` — generated registry of every YARG source id (from the game's OpenSource data).
- `career_builder.py` — the tool.
- `README.md` — this file.

## Quick start

```
1. python career_builder.py regenerate-sources  # rebuild sources.json from a YARG install
2. python career_builder.py scan                # list songs + per-source counts
3. python career_builder.py build               # generate the career

```

Output goes to `output_dir` (default: this folder) as both `<name>.json` (import via
YARG -> Presets -> Career -> Import) and `<name>.preset` (the zipped export form),
where `<name>` is the sanitized career name.

## How songs are referenced

Each song is written as a **Song Tuple**:

```json
{
  "SongTuple": { "Artist": "Blink-182", "Title": "Dammit (Growing Up)", "Source": "ghwt", "Charter": "Neversoft" },
  "Identifier": "SongTuple"
}
```

The four values are read straight from each song folder's `song.ini`:

| Tuple field | song.ini key |
|---|---|
| Title | `name` |
| Artist | `artist` |
| Charter | `charter` (fallback `frets`) |
| Source | `icon` |

## Public vs private

`visibility` in `settings.json` controls which sources are allowed:

- **private** — any source is allowed.
- **public** — the build is **hard-blocked** unless every selected song's source is a general
  custom (`type` `custom`/`charter`) or YARC Launcher content (`yarg`/`yargdlc`/`yarn`).
  Guitar Hero / Rock Band / other-game setlists are never allowed in public careers.

## Source selection

- `source_selection.filter` — restrict to specific source ids (empty = all).
- `source_selection.limit` — cap the number of distinct sources used; sources are ranked by song
  count and the top N are kept.
- `source_selection.weights` — **optional**; if non-empty it overrides `filter`/`limit`. A map of
  `source id -> weight`. The career's target total is split across the listed sources in proportion
  to their weights, so `{"ghwt": 3, "ghwtdlc": 1, "gh3": 1}` gives `ghwt` ~3x the songs of the others.
  Use a small weight for a "filler" source (just tops up the total) and a large weight for the main
  source. Within each source the easiest songs are taken first; the combined list is still sorted by
  difficulty before being split into tiers.

The **default career is 80 songs across 12 tiers** (5/10/5/5/10/5/5/10/5/5/10/5). `scan` prints
this target plus per-source song counts, so you can pick sources whose combined count is near 80
(e.g. `ghwt` = 86, `ghwtdlc` = 155). Whatever you select is re-split across the tiers by
`redistribute`.

## YARG install location

`sources.json` is generated from a YARG install's `StreamingAssets\sources\OpenSource-master`
registry. The `yarg` block in `settings.json` points at which build to use:

- `yarg.install_dir` — the install folder (the one containing `YARG.exe`). Leave `""` to
  auto-detect. `regenerate-sources` scans **all drives (C: first)** for the YARC launcher layout
  (`<drive>:\YARC\YARG Installs\*\installation`) and a few common standalone locations; if it finds
  multiple it lists them and asks you to pick, and if it finds none it prompts for a path. Each
  install is labelled **`Nightly`** or **`Stable`** (read from the launcher's `releaseName`;
  "Stable" = retail/release).
- `yarg.data_dir` — the `LocalLow` profile (`nightly` vs `release`); informational for now.

**Note:** the release/retail build ships only `base` (official GH/RB/YARG sources); the nightly
build also ships `extra` (community/custom sources). Regenerating from a release install will drop
the `custom`/`charter` sources, so point at the nightly build if you need those.

## Difficulty ordering

Songs are sorted by `difficulty.field` (default `diff_guitar`) ascending, easiest first,
then split across the tiers defined in `settings.json`.

## All available sources

`public` column = allowed in a public (postable) career when referenced as a Song Tuple.

| Source | Type | Public | ids |
|---|---|---|---|
| Custom/Unknown | Custom | yes | custom |
| YARG | Game | yes | yarg |
| YARG DLC | Game | yes | yargdlc |
| YARN | Game | yes | yarn |
| Band Hero | Guitar Hero | no | bandhero, bh |
| Band Hero 2 | Guitar Hero | no | bandhero2, bh2 |
| Death Magnetic DLC | Guitar Hero | no | ghmdlc |
| Guitar Hero | Guitar Hero | no | gh, gh1 |
| Guitar Hero 5 | Guitar Hero | no | gh5 |
| Guitar Hero 5 DLC | Guitar Hero | no | gh5dlc |
| Guitar Hero Deluxe | Guitar Hero | no | gh1dx, ghdx |
| Guitar Hero Encore Deluxe | Guitar Hero | no | gh80sdx |
| Guitar Hero Encore: Rocks the 80s | Guitar Hero | no | gh80s |
| Guitar Hero II | Guitar Hero | no | gh2 |
| Guitar Hero II Deluxe | Guitar Hero | no | gh2dx |
| Guitar Hero II Deluxe Customs | Guitar Hero | no | gh2dxcustoms |
| Guitar Hero II Deluxe DLC | Guitar Hero | no | gh2dxdlc |
| Guitar Hero II DLC | Guitar Hero | no | gh2dlc |
| Guitar Hero III DLC | Guitar Hero | no | gh3dlc |
| Guitar Hero III: Legends of Rock | Guitar Hero | no | gh3 |
| Guitar Hero Live | Guitar Hero | no | ghl |
| Guitar Hero On Tour: Decades | Guitar Hero | no | ghotd |
| Guitar Hero On Tour: Modern Hits | Guitar Hero | no | ghotmh |
| Guitar Hero TV | Guitar Hero | no | ghtv |
| Guitar Hero: Aerosmith | Guitar Hero | no | gha |
| Guitar Hero: Metallica | Guitar Hero | no | ghm |
| Guitar Hero: On Tour | Guitar Hero | no | ghot |
| Guitar Hero: Smash Hits | Guitar Hero | no | ghsh |
| Guitar Hero: Van Halen | Guitar Hero | no | ghvh |
| Guitar Hero: Warriors of Rock | Guitar Hero | no | ghwor |
| Guitar Hero: Warriors of Rock DLC | Guitar Hero | no | ghwordlc |
| Guitar Hero: World Tour | Guitar Hero | no | ghwt |
| Guitar Hero: World Tour DLC | Guitar Hero | no | ghwtdlc |
| AC/DC Live: Rock Band Track Pack | Rock Band | no | rbacdc, rbtp_acdc |
| Green Day: Rock Band | Rock Band | no | gdrb, greenday |
| Green Day: Rock Band DLC | Rock Band | no | gdrb_plus, gdrbdlc, gdrbp |
| Lego Rock Band | Rock Band | no | lego, lrb |
| Lost Rock Band Network | Rock Band | no | rbn1lost, rbn_lost, ugc_lost |
| Lost Rock Band Network 1.0 | Rock Band | no | rbn1_lost, ugc1_lost |
| Lost Rock Band Network 2.0 | Rock Band | no | rbn2_lost, rbn2lost, ugc2_lost |
| Rock Band 1 | Rock Band | no | rb1 |
| Rock Band 1 DLC | Rock Band | no | rb1_dlc, rb1dlc |
| Rock Band 2 | Rock Band | no | rb2, rb2_real |
| Rock Band 2 DLC | Rock Band | no | rb2_dlc, rb2dlc |
| Rock Band 3 | Rock Band | no | rb3 |
| Rock Band 3 DLC | Rock Band | no | rb3_dlc, rb3dlc |
| Rock Band 4 | Rock Band | no | rb4 |
| Rock Band 4 DLC | Rock Band | no | rb4_dlc, rb4dlc |
| Rock Band Blitz | Rock Band | no | blitz, rb_blitz, rbb |
| Rock Band Network | Rock Band | no | rbn, rbn1 |
| Rock Band Network 1.0 | Rock Band | no | ugc, ugc1 |
| Rock Band Network 2.0 | Rock Band | no | rbn2, ugc2, ugc_plus |
| Rock Band Rivals | Rock Band | no | rb4_rivals, rb4rivals, rbr |
| The Beatles: Rock Band | Rock Band | no | beatles, tbrb |
| The Beatles: Rock Band DLC | Rock Band | no | beatles_dlc, tbrbdlc |
| 3-UP | Charter | yes | 3up |
| CloneHeroUruguay | Charter | yes | chu |
| Cosmic Latte | Charter | yes | cosmiclatte |
| DaiJyoubs | Charter | yes | daijyoubs |
| DeltaOm3ga | Charter | yes | deltaom3ga |
| donnaken15's Customs | Charter | yes | dk15, donnaken15 |
| Hugh | Charter | yes | hugh |
| JRabes | Charter | yes | JRabes, jrabes |
| Mickelräven | Charter | yes | mickelraven |
| PaletaGalleta | Charter | yes | paletagalleta |
| raphaelgoulart | Charter | yes | goulart |
| thardwardy | Charter | yes | redo, ted |
| Venerabela | Charter | yes | vene |
| 311 Hero | Custom | yes | 311hero |
| A-Z Pack | Custom | yes | a2z |
| Adagio Discography | Custom | yes | adagiodiscog |
| Aeon Bridge | Custom | yes | ab |
| AIRheads | Custom | yes | airheads |
| Angevil Hero | Custom | yes | ah, ah1 |
| Angevil Hero 2 | Custom | yes | ah2 |
| Angevil Hero 3 | Custom | yes | ah3 |
| Angevil Hero 4 | Custom | yes | ah4 |
| Anime Hero | Custom | yes | animehero |
| Anti Hero | Custom | yes | antihero |
| Anti Hero - Beach Episode | Custom | yes | ahbe |
| Anti Hero 2 | Custom | yes | antihero2 |
| Asphalt 9: Legends | Custom | yes | a9 |
| Avenged Sevenfold Mega Pack | Custom | yes | a7x, a7xmegapack |
| Bee Gees: Rock Band | Custom | yes | bgrb |
| BITCRUSHER | Custom | yes | bitcrusher |
| BITCRUSHER DLC | Custom | yes | bitcrusherdlc |
| Black Hole | Custom | yes | blackhole |
| Blanket Statement | Custom | yes | bs, bstatement |
| Bleep Bloop Undercharts | Custom | yes | bleepbloopuc |
| Bleep Bloops | Custom | yes | bleepbloops, generic |
| Bodom Hero | Custom | yes | bodom |
| Brick | Custom | yes | brick |
| Burnout 3: Takedown | Custom | yes | burnout3 |
| C3 Customs | Custom | yes | c3customs, ccc, ugc_c3 |
| C3 Legacy | Custom | yes | c3legacy |
| Carpal Tunnel Hero | Custom | yes | cth, cth1 |
| Carpal Tunnel Hero 1: Remastered | Custom | yes | cth1r |
| Carpal Tunnel Hero 2 | Custom | yes | cth2 |
| Carpal Tunnel Hero 3 | Custom | yes | cth3 |
| Carpal Tunnel Hero 3 DLC | Custom | yes | cth3dlc |
| CASP | Custom | yes | casp |
| CHARTS | Custom | yes | charts |
| CHARTS 2 | Custom | yes | charts2 |
| Chel Hero | Custom | yes | chelhero |
| Chel Hero 2 | Custom | yes | chelhero2 |
| Chill Hanger | Custom | yes | chillhanger |
| Circuit Breaker | Custom | yes | cb |
| Code Red | Custom | yes | codered |
| Community Track Pack 4.5 | Custom | yes | comtp45 |
| Community Track Pack I | Custom | yes | comtpi |
| Community Track Pack II | Custom | yes | comtpii |
| Community Track Pack III | Custom | yes | comtpiii |
| Community Track Pack IV | Custom | yes | comtpiv |
| Community Track Pack V | Custom | yes | comtpv |
| Cow Hero | Custom | yes | cowhero |
| Cow Hero DLC 1 - Bull Conqueror | Custom | yes | cowherodlc1 |
| Cow Hero DLC 2 - Bovine Champion | Custom | yes | cowherodlc2 |
| Cow Hero DLC 3 - Cattle Guardian | Custom | yes | cowherodlc3 |
| Creative Commons Hero | Custom | yes | creativech |
| Custom Songs | Custom | yes | customs |
| Custom Songs Central | Custom | yes | csc |
| Delta's Chart Repository | Custom | yes | dcr |
| Digitizer | Custom | yes | digi, digitizer |
| Disgorodraphy | Custom | yes | disgo, gorod |
| Dissonance Hero | Custom | yes | dissonancehero |
| Djent Hero | Custom | yes | djenth, djenthero |
| Djent Hero Collection | Custom | yes | dhc |
| Djent Hero DLC | Custom | yes | djenthdlc, djentherodlc |
| DJMax | Custom | yes | djmax |
| Emotional Rollercoaster | Custom | yes | emotion |
| Example and Test Charts | Custom | yes | example, examples, test |
| Facelift | Custom | yes | facelift |
| Focal Point | Custom | yes | fp |
| Focal Point 2 | Custom | yes | fp2 |
| Focal Point 3 | Custom | yes | fp3 |
| Fuse Box | Custom | yes | fuse, fusebox |
| Guitar Hero II: Addy's Disc | Custom | yes | addygh |
| Guitar Hero To Rock Band 3 | Custom | yes | ghtorb3 |
| Guitar Hero X | Custom | yes | ghxsetlist |
| Guitar Hero X-II | Custom | yes | ghx2setlist |
| Guitar Zero | Custom | yes | guitarzero, guitarzero132 |
| Guitar Zero 2 | Custom | yes | guitarzero2 |
| Guitar Zero 2 DLC | Custom | yes | guitarzero2dlc, guitarzerodlc |
| Guitar Zero Encore 1: Rocks the '70s | Custom | yes | guitarzeroencore1, gze1 |
| Harmony Hero | Custom | yes | harmonyhero |
| HexaNation | Custom | yes | french |
| Indiependence Day | Custom | yes | indp |
| Initial D The Arcade Setlist | Custom | yes | idta |
| Instru-Metal | Custom | yes | imetal |
| Iron Hand Hero | Custom | yes | ironhandhero |
| J-Rock Band | Custom | yes | jrb |
| Koreaboo Hero | Custom | yes | kh |
| Koreaboo Hero 2 | Custom | yes | kh2 |
| Koreaboo Hero 3 | Custom | yes | kh3 |
| Lane Breakers | Custom | yes | lanebreakers |
| Lisarb 1 | Custom | yes | lisarb, lisarb1 |
| Lisarb 2 | Custom | yes | lisarb2 |
| Lisarb 3 | Custom | yes | lisarb3 |
| Mania Hero | Custom | yes | mania, maniahero, mh_aren, mh_asriel, mh_dex, mh_fluffy, mh_ori, mh_sasquatch, mh_sickliff, mh_skittlecouch, mh_supra |
| Marathon Hero | Custom | yes | marathon |
| Marathon Hero 2 | Custom | yes | marathonhero2 |
| Max Altitude | Custom | yes | ma |
| Meme Songs | Custom | yes | meme |
| MiloHax Customs | Custom | yes | milohax |
| Miscellaneous Packs | Custom | yes | miscellaneous |
| Nirvana Discography | Custom | yes | nirvana, nirvanasp |
| Paradigm | Custom | yes | paradigm |
| Paramore Mega Pack | Custom | yes | paramore, paramoremegapack |
| Phase Shift Guitar Project 4 | Custom | yes | psgp4 |
| Plastic Shred Hero 2 | Custom | yes | psh2 |
| Plastic Shred Hero: Legends of Apahetic Charting | Custom | yes | psh |
| Puppetz Hero I | Custom | yes | ph1 |
| Puppetz Hero II | Custom | yes | ph2 |
| Puppetz Hero III | Custom | yes | ph3 |
| Puppetz Hero IV | Custom | yes | ph4 |
| Rage Quit | Custom | yes | ragequit |
| Redemption Arc | Custom | yes | ra |
| REVOLVED | Custom | yes | revolved |
| RhythmVerse | Custom | yes | rv |
| Rock Band en Español | Custom | yes | rbee |
| S Hero | Custom | yes | s_hero |
| ScoreSpy | Custom | yes | scorespy |
| Shadow of Intent Discography | Custom | yes | soi |
| Small Charters United | Custom | yes | scu, scufd |
| Solo Medleys | Custom | yes | solomedley |
| Suomibiisit | Custom | yes | finnish |
| Symphonic Effect | Custom | yes | se |
| Symphony X Discography Setlist | Custom | yes | sxdisc |
| Synergy | Custom | yes | synergy |
| Teminite | Custom | yes | teminite |
| The Eternal Project | Custom | yes | aep |
| The Fall of Troy Hero | Custom | yes | tfoth |
| Venera Hero 1 | Custom | yes | venera1 |
| Venera Hero 2 | Custom | yes | venera2 |
| Venera Hero 3 | Custom | yes | venera3 |
| Vortex Hero | Custom | yes | vortex_hero, vortexhero |
| World Charts Community | Custom | yes | wcc |
| YoShibyl | Custom | yes | yoshibyl, yoshiog |
| Yuri Anime Pack | Custom | yes | yurianime |
| Zancharted | Custom | yes | zancharted |
| Zero Gravity | Custom | yes | zerogravity |
| Zero Gravity - Space Battle | Custom | yes | zgsb |
| ΩHM | Custom | yes | ohm |
| Clone Hero | Game | no | ch, clonehero |
| DJ Hero | Game | no | djh, djhero |
| DJ Hero 2 | Game | no | djh2, djhero2 |
| DJ Hero 2 DLC | Game | no | djh2dlc, djhero2dlc |
| DJ Hero DLC | Game | no | djhdlc, djherodlc |
| Editor on Fire | Game | no | eof |
| encore | Game | no | encore |
| Fret Smasher | Game | no | fret smasher, fretsmasher |
| Frets on Fire | Game | no | fof |
| Frets on Fire X | Game | no | fofix |
| GITADORA | Game | no | gd |
| Guitar Praise | Game | no | praise |
| Guitar Praise DLC | Game | no | praisedlc |
| Guitar Praise: Expansion Pack 1 | Game | no | praiseexpansion |
| Guitar Praise: Stryper | Game | no | stryper |
| GuitarFreaks | Game | no | gf1 |
| GuitarFreaks 2ndMIX & DrumMania | Game | no | gf2dm1 |
| JAMband | Game | no | jamband |
| JAMband DLC | Game | no | jambanddlc |
| Phase Shift | Game | no | phaseshift |
| PopStar Guitar | Game | no | popstarguitar |
| PowerGig: Rise of the SixString | Game | no | pg |
| PowerGig: Rise of the SixString DLC | Game | no | pgdlc |
| Rock Revolution | Game | no | rr |
| Rock Revolution DLC | Game | no | rrdlc |
| Santa Rockstar | Game | no | santa, santahd, santarockstar, santarockstarhd |
| SingStar Guitar | Game | no | singstarguitar |
| Band Hero DLC | Guitar Hero | no | bhdlc |
| Band Hero DS | Guitar Hero | no | bhds |
| Pearl Jam: Rock Band | Rock Band | no | pearljam, rbpj |
| Rock Band Country Track Pack | Rock Band | no | rbtp_country_1, rbtpc |
| Rock Band Country Track Pack 2 | Rock Band | no | rbtp_country_2, rbtpc2 |
| Rock Band Metal Track Pack | Rock Band | no | rbtp_metal, rbtpm |
| Rock Band Track Pack Vol. 1 | Rock Band | no | rbtp1, rbtp_vol_1 |
| Rock Band Track Pack Vol. 2 | Rock Band | no | rbtp2, rbtp_vol_2 |
| Rock Band Track Pack: Classic Rock | Rock Band | no | rbtp_classic_rock, rbtpcr |
| Rock Band VR | Rock Band | no | rbvr |
