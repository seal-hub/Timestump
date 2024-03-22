## Automated Accessibility Analysis of Dynamic Content Changes on Mobile Apps
### [Source Code of TIMESTUMP](https://github.com/timestump/timestump/tree/main/Source%20Code)

### [Study for the Precision of Captured Data](https://github.com/timestump/timestump/blob/main/Data%20Capturing%20Accuracy/Data%20Capturing%20Accuracy.md)

### Problematic Dynamic Content Changes with Algorithms

#### Latent Appearing Content

[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/Fuelio.png)](https://github.com/timestump/timestump/blob/main/Media/fuelio.mp4
)

[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/fuelio.gif)]()


<!-- <img src="fuelio.mp4" alt="Appeared buttons remain unknown to screen reader users" width="150"/> -->

```python
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initFrame = NodeTree_t1

currentFocus = getA11yFocus(initFrame)
LAE = set()

for e in finalFrame:
    if e not in initFrame and e in sources and isAbove(e, currentFocus) and not e.isLiveRegion:
        LAE.add(e)

return LAE
```

#### Latent Disappearing Content

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Burn.png)](https://github.com/timestump/timestump/blob/main/Media/burn.gif
)

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/burn.gif)]()

```python
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initFrame = NodeTree_t1

currentFocus = getA11yFocus(initFrame)

prunedInit = getSubtreeInBounds(initFrame, sources)
prunedFinal = getSubtreeInBounds(finalFrame, sources)

LDE = set()

for e in prunedInit:
    if e not in prunedFinal and isBelow(e, currentFocus) and not e.isLiveRegion:
        LDE.add(e)

return LDE
```
#### Latent Short-lived Content

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Spotify.png)](https://github.com/timestump/timestump/blob/main/Media/spotify.gif 
)

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/spotify.gif)]()

```python
# Create pairs of events where type is WINDOW_CONTENT_CHANGED and S1 is within S2
pairs = [(e1.source, e2.source) for e1, e2 in a11yEvents if e1.type == e2.type == WINDOW_CONTENT_CHANGED and isWithin(e1.source, e2.source)]  

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initFrame = NodeTree_t1

SLE = set()

for S1, S2 in pairs:
    if S1 not in initFrame and S2 in finalFrame and (not S1.isLiveRegion or S1.isClickable):
        SLE.add(S1)

return SLE
```
#### Latent Moving Content

[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/Autozone.png)](https://github.com/timestump/timestump/blob/main/Media/autozone.mp4 
)

[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/autozone.gif)]()

```python
# Extract sources from events with type WINDOW_CONTENT_CHANGED
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initFrame = NodeTree_t1

currentFocus = getA11yFocus(initFrame)
MDE = set()

for e_initial in initialElements:
    for e_final in finalFrame:
        if isEquivalent(e_initial, e_final) and e_initial.bounds != e_final.bounds and e_initial in sources and e_final in sources and (isAbove(e_final, currentFocus) or isOutOfScreenBounds(e_final)):
            MDE.add(e_final)

return MDE
```
#### Latent Content Modification

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Fuelio2.png)](https://github.com/timestump/timestump/blob/main/Media/fuelio2.gif 
)

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/fuelio2.gif)]()

```python
# Set up initial and final frames
initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initFrame = NodeTree_t1
    
changedElements = set()

# Define the procedure to detect changes between two frames
def DetectChanges(frameA, frameB):
    for e1 in frameA:
        for e2 in frameB:
            if isEquivalent(e1, e2) and hash(e1) != hash(e2) and not e2.isLiveRegion:
                changedElements.add(e2)

# Detect changes between initFrame and finalFrame
DetectChanges(initFrame, finalFrame)

# Return the set of changed elements
return changedElements
```
### RQ1 Subject Apps

| ID   | App Name                     | Package Name                                         | Installs | Rate | Category          |
| ---- | ---------------------------- | ---------------------------------------------------- | -------- | ---- | ----------------- |
| P1   | Autozone                     | com.autozone.mobile                                  | >5M      | 4.7  | Auto & Vehicles   |
| P2   | Duolingo                     | com.duolingo                                         | >500M    | 4.7  | Education         |
| P3   | Forest                       | cc.forestapp                                         | >10M     | 4.7  | Productivity      |
| P4   | Gratitude                    | com.northstar.gratitude                              | >1M      | 4.9  | Lifestyle         |
| P5   | Motivation                   | com.hrd.motivation                                   | >5M      | 4.8  | Health & Fitness  |
| P6   | Starbucks                    | com.starbucks.mobilecard                             | >10M     | 4.8  | Food & Drink      |
| P7   | TicketMaster                 | com.ticketmaster.mobile.android.na                   | >10M     | 2.9  | Events            |
| P8   | Spotify                      | com.spotify.music                                    | >1B      | 4.4  | Music & Audio     |
| P9   | H&M                          | com.hm.goe                                           | >50M     | 4.7  | Lifestyle         |
| P10  | File Manager                 | com.mi.android.globalFileexplorer                    | >1B      | 4.7  | Tools             |
| G1   | Booking.com                  | com.booking                                          | >500M    | 4.6  | Travel & Local    |
| G2   | Easy Bills Reminder          | com.aa3.easybillsreminder                            | >100K    | 4.5  | Finance           |
| G3   | Burn                         | com.alphasoft.burn                                   | >100     | NA   | Education         |
| G4   | Dictionary.com               | com.dictionary                                       | >10M     | 4.7  | Books & Reference |
| G5   | ESPN                         | com.espn.score_center                                | >50M     | 4.3  | Sports            |
| G6   | Calorie Counter by FatSecret | com.fatsecret.android                                | >50M     | 4.6  | Health & Fitness  |
| G7   | Fuelio                       | com.kajda.fuelio                                     | >1M      | 4.4  | Auto & Vehicle    |
| G8   | Life360                      | com.life360.android.safetymapd                       | >100M    | 4.6  | Lifestyle         |
| G9   | Master Lock Vault Enterprise | com.masterlock.enterprise.vaultenterprise            | >100K    | 4.1  | Lifestyle         |
| G10  | Nike                         | com.nike.omega                                       | >50M     | 4.7  | Shopping          |
| G11  | Weee!                        | com.sayweee.weee                                     | >1M      | 4.8  | Food & Drink      |
| G12  | Norton Secure VPN            | com.symantec.securewifi                              | >10M     | 4.4  | Tools             |
| G13  | Triplt                       | com.tripit                                           | >5M      | 4.7  | Travel & Local    |
| G14  | ToonMe                       | com.vicman.toonmeapp                                 | >50M     | 4.6  | Photography       |
| G15  | Vimeo                        | com.vimeo.android.videoapp                           | >10M     | 3.7  | Entertainment     |
| G16  | Yelp                         | com.yelp.android                                     | >50M     | 4.6  | Food & Drink      |
| G17  | The Clock                    | hdesign.theclock                                     | >1M      | 4.2  | Productivity      |
| G18  | King James Bible             | kjv.bible.kingjamesbible                             | >50M     | 4.8  | Books & Reference |
| G19  | Lyft                         | me.lyft.android                                      | >50M     | 4.9  | Maps & Navigation |
| G20  | To-Do-List                   | todolist.scheduleplanner.dailyplanner.todo.reminders | >10M     | 4.6  | Productivity      |


<!--
**timestump/timestump** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
