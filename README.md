# Buddy-App
This is the entire souce code for my Buddy App. No Image Files Included


So generally to get up and running on this project you are to put it on local PC then Create 2 new Folders in the folder containing this repositories content mainly -'Animations' and 'Splash' Folder. In the splash folder, you are to put in a single .png file by the name of 'splash_screen.png', it is supposed to be a 640x360 image but who cares ?, you go for whatever size you think is best for your custom build. 

In the main folder (the one with main.py) , you are to put a single .png file by the name of face_idle.png ,this ismage is to be the static- mostly viewed face of the desktop companion so i advise you to make it like a starting and ending face of allll your animations inorder for it to be a smooth transition from one state to the other.

You are to create 4 Seperate folders within the Animations folder by the names of Idle ,Sarcasm ,Talking and Warning. These 4 folders are where you're  gonna place your animation frames. For best performance, make sure they are all of small size, like less than 500kb each - the smaller the better.

THe Idle folder must contain 5 Idles 150 frames each ,meaning its a 750 frame image sequence you're gonna stuff in there. My code very much supports 1080x1080 frame resolution for ecery png you are to add as an animation to the animation folder. Insure the face_idle.png is also 1080*1080(same as animations). In the Sarcasm folder, put in a 150 frame image sequence beginning with 0001.png and ending with 0150.png ,same goes for Talking and Warning.

The animations currently work like this --> Buddy turns on ,shows you a splashscreen for a second then vanishes (this gives the user confirmation that he actually launched bro)--> Buddy loads image files and scripts in background(again ,how fast he loads depends on image file size)--> Once he successfully loads all assets in RAM ,he launches visibly on screen. The Idles(750 frames), will cycle randomly every 15 to 60 seconds. The break point will be the face_idle.png which will act as a middle ground, a decoy whilst the timer runs for the next animation. Whenever Buddy has something to say, he will give off the Talking animation and sometimes when you ignore him, he will give off the Sarcasm animation and when something is wrong with your PC, he'll give off the Warning Animation. 

I use Blender to create the animations and Vs code for the coding and a few aI apps on debugging errors and it is very cool. Feel free to Modify this wonderful App however yo wish ,just don't do illegal activities with it .The code is clean ,the Files are Clean, everything is clean. 

I'm free to chat whenever for whatever cause. Even a 'Thank you' is cool. Have Fun.

By Angel .T Amos
