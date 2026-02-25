# THIS IS A PERSONAL PROJECT, MAINLY TO INTEGRATE WITH WANDERER, IS CLEARLY NOT READY FOR PRIMETIME, AND LIKELY WILL NEVER BE! I highly encourage folks to continue with the excellent https://github.com/secondfry/shortcircuit

# Short Circuit

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/mogglemoss/shortcircuit)](https://github.com/mogglemoss/shortcircuit/releases)
[![Build Application](https://github.com/mogglemoss/shortcircuit/actions/workflows/build.yml/badge.svg)](https://github.com/mogglemoss/shortcircuit/actions/workflows/build.yml)

![Short Circuit UI](docs/screenshot.jpg) **Short Circuit** is an advanced, standalone routing and navigation tool for EVE Online. It calculates the absolute shortest path between solar systems by seamlessly blending standard Stargate routes with live wormhole connections pulled from your favorite 3rd-party mapping tools.

Whether you're running logistics, hunting targets, or just daytripping in J-Space, Short Circuit takes the guesswork out of traversing New Eden.

## ✨ Features

* **Intelligent Hybrid Routing**: Calculate optimized paths across High Sec, Low Sec, Null Sec, and Wormhole space in seconds.
* **EVE SSO Integration**: Log in securely with your EVE Online account to automatically fetch your current in-game location and set route waypoints directly in the game client.
* **Granular Route Filtering**:
  * **Wormhole Restrictions**: Filter potential paths by ship size (e.g., Frigate, Cruiser), and choose to ignore End of Life (EOL) holes, critical mass holes, or wormholes older than a specified time limit.
  * **Security Prioritization**: Fine-tune your route using custom sliders (0-100) to weight your preference for High Sec, Low Sec, Null Sec, or WH space.
  * **Avoidance List**: Blacklist specific solar systems or entire regions to keep your route out of known gate camps and dangerous space.
* **Fleet-Friendly Exporting**: 
  * Copy your route in a simplified text format perfect for fleet chat (`Jita --> ... --> Iyen-Oursta [HVE-768] ~~> J153528`).
  * Copy the full, detailed instruction table with a single click.

## 📡 Supported Mapping Sources

Short Circuit pulls live chain data directly from the most popular wormhole mapping tools in the EVE community:

* **[Eve-Scout](https://eve-scout.com/)** (Automatic Thera & Turnur connections)
* **[Tripwire](https://tripwire.eve-apps.com/)**
* **[Wanderer](https://wanderer.space/)**

## 🚀 Installation

*(Note: If you provide pre-compiled binaries, you can download the latest version from the [Releases](https://github.com/mogglemoss/shortcircuit/releases) page.)*

**Running from Source:**
Make sure you have Python 3 installed, then clone the repository and install the dependencies:

```bash
git clone [https://github.com/mogglemoss/shortcircuit.git](https://github.com/mogglemoss/shortcircuit.git)
cd shortcircuit
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
python main.py  # Replace with your actual entry point script if different
```

## ⚙️ Quick Start Guide
Connect your Sources: Click Wormhole Sources at the top right to configure and enable your preferred mappers (Tripwire, Pathfinder, Wanderer) and Eve-Scout.

Log in with EvE: (Optional) Authenticate via EVE SSO to enable the "Get player location" and "Set destination" features.

Set your Route: Enter your Source and Destination systems in the Navigation panel.

Configure Restrictions: Adjust ship size limits, security sliders, and avoidance lists based on what you are flying.

Find Path: Hit Find path to generate your route. Jump instructions, signature IDs, and wormhole status will be displayed clearly in the Route Results table.

## 🙌 Credits & Acknowledgments
A massive shout-out to the original creators and maintainers who laid the groundwork for this tool:

farshield - For designing and building the original version of Short Circuit.

secondfry - For their long-term maintenance of the secondfry/shortcircuit fork, which is keeping the application alive and functional for the EVE community through years of API changes.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
