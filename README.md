## Automated Accessibility Analysis of Dynamic Content Changes on Mobile Apps
### [Source Code of TIMESTUMP](https://github.com/timestump/timestump/tree/main/Source%20Code)



### Problematic Dynamic Content Changes with Algorithms

When you click on the images below, you will be directed to either a **video** or a **GIF** that better illustrates the issue.

#### Latent Appearing Content

[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/Fuelio.png)](https://github.com/timestump/timestump/blob/main/Media/fuelio.mp4
)


<!-- <img src="fuelio.mp4" alt="Appeared buttons remain unknown to screen reader users" width="150"/> -->

```python
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initialElements = NodeTree_t1

currentFocus = getA11yFocus(initFrame)
LAE = set()

for e in finalFrame:
    if e not in initFrame and e in sources and isAbove(e, currentFocus) and not e.isLiveRegion:
        LAE.add(e)

return LAE
```

[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Burn.png)](https://github.com/timestump/timestump/blob/main/Media/burn.gif
)

#### Latent Disappearing Content

```python
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initialElements = NodeTree_t1

currentFocus = getA11yFocus(initFrame)

prunedInit = getSubtreeInBounds(initFrame, sources)
prunedFinal = getSubtreeInBounds(finalFrame, sources)

LDE = set()

for e in prunedInit:
    if e not in prunedFinal and isBelow(e, currentFocus) and not e.isLiveRegion:
        LDE.add(e)

return LDE
```
[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Spotify.png)](https://github.com/timestump/timestump/blob/main/Media/spotify.gif 
)

#### Latent Short-lived Content

```python
# Create pairs of events where type is WINDOW_CONTENT_CHANGED and S1 is within S2
pairs = [(e1.source, e2.source) for e1, e2 in a11yEvents if e1.type == e2.type == WINDOW_CONTENT_CHANGED and isWithin(e1.source, e2.source)]  

finalFrame = NodeTree_t2
initFrame = NodeTree_t0

if WindowTransitionObserved(a11yEvents):
    initialElements = NodeTree_t1

SLE = set()

for S1, S2 in pairs:
    if S1 not in initFrame and S2 in finalFrame and (not S1.isLiveRegion or S1.isClickable):
        SLE.add(S1)

return SLE
```
[![Watch the video](https://github.com/timestump/timestump/blob/main/Media/Autozone.png)](https://github.com/timestump/timestump/blob/main/Media/autozone.mp4 
)

#### Latent Moving Content

```python
# Extract sources from events with type WINDOW_CONTENT_CHANGED
sources = [event.source for event in a11yEvents if event.type == WINDOW_CONTENT_CHANGED]

initFrame = NodeTree_t0
finalFrame = NodeTree_t2

if WindowTransitionObserved(a11yEvents):
    initialElements = NodeTree_t1

currentFocus = getA11yFocus(initFrame)
MDE = set()

for e_initial in initialElements:
    for e_final in finalFrame:
        if isEquivalent(e_initial, e_final) and e_initial.bounds != e_final.bounds and e_initial in sources and e_final in sources and (isAbove(e_final, currentFocus) or isOutOfScreenBounds(e_final)):
            MDE.add(e_final)

return MDE
```
[![Watch the gif](https://github.com/timestump/timestump/blob/main/Media/Fuelio2.png)](https://github.com/timestump/timestump/blob/main/Media/fuelio2.gif 
)

#### Latent Content Modification

```python
# Set up initial, intermediate, and final frames
initFrame = NodeTree_t0
midFrame = NodeTree_t1
finalFrame = NodeTree_t2
changedElements = set()

# Define the procedure to detect changes between two frames
def DetectChanges(frameA, frameB):
    for e1 in frameA:
        for e2 in frameB:
            if isEquivalent(e1, e2) and hash(e1) != hash(e2) and not e2.isLiveRegion:
                changedElements.add(e2)

# Detect changes between initFrame and midFrame
DetectChanges(initFrame, midFrame)

# Detect changes between midFrame and finalFrame
DetectChanges(midFrame, finalFrame)

# Detect changes between initFrame and finalFrame
DetectChanges(initFrame, finalFrame)

# Return the set of changed elements
return changedElements
```
### Subject Apps

| Id  | App Name                                  | Package Name                                         | Installs   | Rate | Category      |
|-----|-------------------------------------------|------------------------------------------------------|------------|------|---------------|
| P1  | Instagram                                 | com.instagram.android                                | 1000000000 |  4.1 | Social        |
| P2  | FacebookLite                              | com.facebook.lite                                    | 1000000000 |  4.1 | Social        |
| P3  | Wish                                      | com.contextlogic.wish                                |  500000000 |  4.6 | Shopping      |
| P4  | Zoom                                      | us.zoom.videomeetings                                |  500000000 |  4.4 | Business      |
| P5  | Tubi                                      | com.tubitv                                           |  100000000 |  4.8 | Entertainment |
| P6  | Shein                                     | com.zzkko                                            |  100000000 |  4.8 | Shopping      |
| P7  | MicrosoftTeams                            | com.microsoft.teams                                  |  100000000 |  4.7 | Business      |
| P8  | Booking                                   | com.booking                                          |  100000000 |  4.6 | Travel        |
| P9  | FileMaster                                | com.root.clean.boost.explorer.filemanager            |  100000000 |  4.5 | Tools         |
| P10 | Life360                                   | com.life360.android.safetymapd                       |  100000000 |  4.5 | Lifestyle     |
| P11 | MovetoiOS                                 | com.apple.movetoios                                  |  100000000 |  2.9 | Tools         |
| P12 | Bible                                     | kjv.bible.kingjamesbible                             |   50000000 |  4.9 | Books         |
| P13 | ToonMe                                    | com.vicman.toonmeapp                                 |   50000000 |  4.6 | Photography   |
| P14 | OfferUp                                   | com.offerup                                          |   50000000 |  4.3 | Shopping      |
| P15 | ESPN                                      | com.espn.score_center                                |   50000000 |    4 | Sports        |
| P16 | Nike                                      | com.nike.omega                                       |   10000000 |  4.5 | Shopping      |
| P17 | Roku                                      | com.roku.remote                                      |   10000000 |  4.4 | Entertainment |
| P18 | Venmo                                     | com.venmo                                            |   10000000 |  4.2 | Finance       |
| P19 | Lyft                                      | me.lyft.android                                      |   10000000 |  3.8 | Navigation    |
| P20 | Expedia                                   | com.expedia.bookings                                 |   10000000 |  3.5 | Travel        |
| A1  | YONO                                      | com.sbi.lotusintouch                                 |  100000000 |  4.1 | Finance       |
| A2  | NortonVPN                                 | com.symantec.securewifi                              |   10000000 |  4.3 | Tools         |
| A3  | DigitalClock                              | com.andronicus.ledclock                              |   10000000 |  4.1 | Tools         |
| A4  | To-Do-List                                | todolist.scheduleplanner.dailyplanner.todo.reminders |    5000000 |  4.7 | Productivity  |
| A5  | HTTP-Injector                             | com.evozi.injector.lite                              |    1000000 |  4.5 | Tools         |
| A6  | Estapar                                   | br.com.estapar.sp                                    |    1000000 |  4.3 | Vehicles      |
| A7  | com.masterlock.enterprise.vaultenterprise | com.masterlock.enterprise.vaultenterprise            |      50000 |  4.2 | Lifestyle     |
| A8  | com.spinearnpk.pk                         | com.spinearnpk.pk                                    |      50000 |  3.8 | Finance       |
| A9  | MyCentsys                                 | com.CenturionSystems.MyCentsysPro                    |      10000 | -    | House         |
| A10 | HManager                                  | com.chsappz.hmanager                                 |      10000 |  4.2 | Productivity  |
| A11 | Greysheet                                 | com.cdn.greysheet                                    |      10000 |    4 | Lifestyle     |
| A12 | com.cegid.cashmanager                     | com.cegid.cashmanager                                |       5000 | -    | Business      |
| A13 | MGFlasher                                 | com.mgflasher.app                                    |       5000 |  4.2 | Vehicles      |
| A14 | com.cryptzone.appgate.xdp                 | com.cryptzone.appgate.xdp                            |       5000 |  3.5 | Business      |
| A15 | Newcatsle                                 | au.gov.nsw.newcastle.app.android                     |       1000 | -    | Lifestyle     |
| A16 | com.freemanhealth.EmployeePortal          | com.freemanhealth.EmployeePortal                     |       1000 |  4.2 | Tools         |
| A17 | io.cordova.myapp6baa2d                    | io.cordova.myapp6baa2d                               |        100 | -    | Health        |
| A18 | AuditManager                              | com.focusinformatica.AuditManagerAzimutBenetti       |         50 | -    | Productivity  |
| A19 | com.murder.eyez                           | com.murder.eyez                                      |         50 | -    | Entertainment |
| A20 | com.alphasoft.burn                        | com.alphasoft.burn                                   |          1 | -    | -             |
| L1  | Soundcloud                                | com.soundcloud.android                               |  100000000 |  4.7 | Music         |
| L2  | Walmart                                   | com.walmart.android                                  |   50000000 |  4.4 | Shopping      |
| L3  | Yelp                                      | com.yelp.android                                     |   50000000 |    4 | Food          |
| L4  | GeekShopping                              | com.contextlogic.geek                                |   10000000 |  4.6 | Shopping      |
| L5  | Dictionary                                | com.dictionary                                       |   10000000 |  4.6 | Books         |
| L6  | FatSecret                                 | com.fatsecret.android                                |   10000000 |  4.6 | Health        |
| L7  | Cookpad                                   | com.mufumbo.android.recipe.search                    |   10000000 |  4.6 | Food          |
| L8  | SchoolPlanner                             | daldev.android.gradehelper                           |   10000000 |  4.4 | Education     |
| L9  | Checkout51                                | com.c51                                              |   10000000 |  4.2 | Shopping      |
| L10 | Vimeo                                     | com.vimeo.android.videoapp                           |   10000000 |    4 | Entertainment |
| L11 | TripIt                                    | com.tripit                                           |    5000000 |  4.8 | Tavel         |
| L12 | ZipRecruiter                              | com.ziprecruiter.android.release                     |    5000000 |  4.8 | Business      |
| L13 | Feedly                                    | com.devhd.feedly                                     |    5000000 |  4.3 | News          |
| L14 | Fuelio                                    | com.kajda.fuelio                                     |    1000000 |  4.5 | Vehicles      |
| L15 | BudgetPlanner                             | com.colpit.diamondcoming.isavemoney                  |    1000000 |  4.4 | Finance       |
| L16 | TheClock                                  | hdesign.theclock                                     |    1000000 |  4.4 | Productivity  |
| L17 | BillReminder                              | com.aa3.easybillsreminder                            |     100000 |  4.5 | Finance       |


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
