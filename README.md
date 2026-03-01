# Short Circuit

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/mogglemoss/shortcircuit)](https://github.com/mogglemoss/shortcircuit/releases)
[![Build Status](https://github.com/mogglemoss/shortcircuit/actions/workflows/build.yml/badge.svg)](https://github.com/mogglemoss/shortcircuit/actions/workflows/build.yml)

> ⚠️ This is a personal project. It is not ready for primetime and, if past performance is any indicator, it may never be. If you require something stable, maintained, and built by someone who knew what they were doing from the start, please see [secondfry's defacto version](https://github.com/secondfry/shortcircuit). That one has adults in charge. This one has me, [Cormorant Fell](https://evewho.com/character/93594488).

![Short Circuit UI](docs/Daytripper.png)

**Short Circuit** is an advanced, standalone routing and navigation tool for EVE Online. It calculates the absolute shortest path between solar systems by seamlessly blending standard stargate routes with live wormhole connections pulled from your favorite third-party mapping tools.

Whether you're running logistics, hunting targets, or daytripping through J-space with the quiet confidence of someone who has absolutely no idea what's on the other side of that wormhole, Short Circuit takes the guesswork out of traversing New Eden — and replaces it with a different, more interesting set of mistakes. Progress.

---

## ✨ Features

![Short Circuit Config](docs/Daytripperconfig.png)

**Intelligent Hybrid Routing** calculates optimized paths across High Sec, Low Sec, Null Sec, and Wormhole space in seconds. The routing engine builds a transient graph from resolved live data, computes the shortest path, and silently respects your avoidance lists and wormhole size restrictions without once asking for your reasons. It's doing an enormous amount of math. An acknowledgment would not go unappreciated.

**Multi-Source Aggregation** connects simultaneously to multiple mapping tools — your corp's Tripwire instance, your personal Wanderer map, Eve-Scout, and more, all at once. Multiple accounts from the same provider are fully supported, because sometimes you have trust issues and that's fine. All incoming data is funneled into a centralized **Connection Database** that handles deduplication, conflict resolution, and freshness tracking. When sources disagree on wormhole status — and they will disagree — it favors the most recently updated data. This is as close to wisdom as software gets.

**Supported mapping platforms:**

![Short Circuit Sources](docs/Daytrippersources.png)
- **[Eve-Scout](https://eve-scout.com/)** — Automatic Thera & Turnur connections, delivered silently and without ceremony
- **[Tripwire](https://tripwire.eve-apps.com/)** — Full support with per-source toggles and targeted refresh
- **[Wanderer](https://wanderer.space/)** — Full support with per-source toggles and targeted refresh

**Granular Route Filtering** gives you fine-grained control over which paths Short Circuit will even consider dignifying with a response:

- **Wormhole Restrictions** — Filter by ship size (Frigate, Cruiser, etc.), exclude End of Life holes, exclude critical mass holes, or ignore wormholes older than a specified time limit. For pilots who have learned, through costly experience, that not all holes are created equal.
- **Security Prioritization** — Four sliders (1–100) let you express your nuanced personal feelings about High Sec, Low Sec, Null Sec, and WH space. Equal values disable the feature entirely. Set Null Sec to 100 and the router will heroically thread you through three consecutive wormholes before it will so much as glance at a null gate. The router has opinions. They are adjustable.
- **Avoidance List** — Blacklist specific solar systems or entire regions. Short Circuit does not ask why. Short Circuit understands.

**EVE SSO Integration** (optional) reads your current in-game location automatically and sets route waypoints directly in the client. The tool works perfectly without it. You'll simply be required to type your location manually, like some kind of animal.

**Fleet-Friendly Exporting** copies your route as clean fleet-chat text (`Jita --> ... --> Iyen-Oursta [HVE-768] ~~> J153528`) or as a full detailed instruction table with jump instructions, signature IDs, and wormhole status — all with a single click. Efficient. Professional. Deeply unlikely to save you from a smartbomb.

**Status Bar Integration** provides real-time feedback: quick source toggles, targeted per-source manual refresh, and relative "Last Updated" freshness timestamps for every active provider. Because stale wormhole data is not a bug. It is a complimentary lesson, delivered at market rates.

---

## ESI Scopes

Short Circuit requests exactly two ESI scopes. Not three. Two.

| Scope | Why |
|---|---|
| `esi-location.read_location.v1` | Reads your current system so you don't have to type it |
| `esi-ui.write_waypoint.v1` | Sets your in-game destination automatically |

No wallet. No mail. No corp APIs. No scanning your bookmarks, your contacts, your kill rights, or your browser history. It asks only for what it uses. We understand this is, in the current landscape, a remarkable restraint.

---

## 🚀 Installation

Pre-compiled binaries are available on the [Releases page](https://github.com/mogglemoss/shortcircuit/releases) for those who prefer their software pre-assembled.

**Running from Source** — Python 3 required. A willingness to read error messages helps but is not strictly mandatory:
```bash
git clone https://github.com/mogglemoss/shortcircuit.git
cd shortcircuit
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

SDE database files are automatically checked and downloaded from [Fuzzwork](https://github.com/fuzzysteve) during the build process. Thank you, fuzzysteve (Steve Ronuken) — a true and tireless pillar of this community, who has quietly enabled more third-party tools than anyone will ever properly document. He deserves more credit than he gets, and he gets quite a lot.

---

## ⚙️ Quick Start

1. **Connect your sources** — Click *Wormhole Sources* in the top right to configure Tripwire, Wanderer, and Eve-Scout
2. **Log in with EVE** *(optional)* — Authenticate via EVE SSO to enable auto-location and in-client waypoint setting
3. **Set your route** — Enter source and destination systems in the Navigation panel
4. **Configure restrictions** — Set ship size limits, adjust security sliders, and populate your avoidance list based on what you're flying and who is currently motivated to kill you specifically
5. **Hit Find Path** — Jump instructions, signature IDs, and wormhole status appear in the Route Results table. What you do with this information is entirely your own affair.

---

## How It Works

Short Circuit reconstructs its own version of the EVE solar map from the `mapSolarSystemJumps` table of the Static Data Export database — a painstaking process that the software completes in the background without complaint. This base map is then extended with live wormhole connections aggregated from all configured third-party sources.

All incoming data flows into the centralized **Connection Database**, which applies three ruthlessly pragmatic principles:

1. **Deduplication** — The same connection reported by multiple sources is counted once. Democracy has limits.
2. **Conflict Resolution** — Permanent gates take priority over transient wormholes. The universe has rules, even if players don't.
3. **Freshness Tracking** — When sources disagree on wormhole status, the most recently updated data wins. The past is unreliable. We've made our peace with that.

The routing engine constructs a transient graph from this resolved data and computes the shortest path in accordance with your avoidance lists and size restrictions.

**Security prioritization** assigns an "effort" weight (1–100) to each jump type: HS, LS, NS, and WH. Equal weights across all four disable the system entirely, treating a null sec gate and a high sec gate as morally equivalent, which they are not. Raise any value and the router will work increasingly hard to avoid that jump type — routing around null sec, for instance, until avoiding it would cost more jumps than it saves. Configure it to match your risk tolerance, your ship type, and the number of losses you've had this week.

---

## Managing Map Sources

The **Wormhole Sources** dialog is the unified interface for all your data providers. Add, remove, and configure Tripwire, Wanderer, and Eve-Scout in one place. The built-in "Test Connection" feature verifies credentials immediately, so you can confirm a source is working before you trust your route to it. The status bar provides per-source freshness timestamps, quick enable/disable toggles, and targeted manual refresh for when a source requires gentle encouragement.

---

## A Note on Reliability

Wormholes are fickle. There's a reason it's called Spooky Space. Routes expire. Intel goes stale. Connections collapse while you're still jumping through them, which is an experience that builds character whether you want it to or not.

**Short Circuit finds the best path based on what is known right now.** It cannot predict the future. It cannot account for the K162 that opened thirty seconds ago. It absolutely cannot stop that cloaked Loki from decloaking directly on your face, and frankly, nothing can.

Fly accordingly.

---

## 🙌 Credits & Acknowledgments

- **[farshield](https://github.com/farshield/shortcircuit)** — Built the original Short Circuit. An absolute legend who started all of this.
- **[secondfry](https://github.com/secondfry/shortcircuit)** — Kept the lights on through years of ESI changes and CCP's creative approach to API stability. Also a legend. Arguably more of a legend, given the sustained and thankless nature of the effort.
- **[mogglemoss](https://github.com/mogglemoss/shortcircuit)** / [Cormorant Fell](https://evewho.com/character/93594488) — Added multi-source aggregation, Wanderer support, made it prettier, introduced an undisclosed number of new bugs, and wrote this README. Proud alumni of [WiNGSPAN Delivery Services](https://www.torpedodelivery.com/), where the torpedoes were always free and the targets were always surprised.

---

## License

MIT. Do what you want with it. Fork it, improve it, quietly fix my bugs and pretend they were always yours. Just don't blame me when you jump a crit hole and lose your billion-ISK pod.

That one is entirely on you. We both know it. 

---

Fly weird,

— [Cormorant Fell](https://evewho.com/character/93594488), probably

---

*This tool uses the [EVE Online ESI API](https://esi.evetech.net). It is not affiliated with or endorsed by CCP Games. EVE Online, EVE, the EVE logo, and all related art, images, and materials are the intellectual property of CCP hf., used with permission under the [CCP Developer License Agreement](https://developers.eveonline.com/resource/license-agreement).*