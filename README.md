# Masonry Wall Simulator

For this assignment, we'd like you to implement a small interactive program to simulate and visualize the build plan for a masonry wall, one brick at the time. On top of the visualization, we’d want you to come up with an efficient algorithm to calculate a build order that optimizes for total time spent building.

##Features
-Four different bonds (Stretcher, Flemish, English, and Wild)
-Computes exactly how many full (210 mm) vs. half (100 mm) bricks fit per row.
-Draws the complete wall outline in a light shade; built bricks fill in dark when you press Enter.
-Optimized Build Order
-Uses a “min-movement” algorithm to group bricks into 800 mm × 1300 mm strides, minimizing robot moves.
-Each stride is assigned a unique color so you can see which bricks are laid in one continuous go.
-Interactive Visualization 
-> Press Enter to build the next brick in the optimized order.
-> Press Space to return to bond selection and regenerate the wall under a different pattern.

# Prerequisites
-Python 3.7 or later
-pip3 (Python 3’s package installer)
That’s it—no other libraries are required, as we install Pygame automatically.

# Installation
1- Clone or unzip this repository so that you have these files in one directory:
main.py
gui_wall_visualizer.py
install.sh
README.md

2- Make the install script executable (macOS/Linux):
`` `chmod +x install.sh` ``  

3- Run the install script:
`` `./install.sh` ``  

This script will:
- Check for python3 and attempt to install it if missing (on Linux: apt-get or yum; on macOS: brew).
- Ensure pip3 is available.
- Upgrade pip3 to the latest version.
- Install the pygame package.
NOTE: If your OS cannot auto-install Python, the script will instruct you to install Python 3 manually.

# Running the Simulator
Once installation completes, run:
`` `python3 gui_wall_visualizer.py` ``  
