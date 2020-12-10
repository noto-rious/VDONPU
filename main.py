from discord.ext import commands
import discord
import json
import os, time, datetime, requests, codecs
import urllib.parse
from bs4 import BeautifulSoup
import asyncio
import sys
import html
from getpass import getpass
from colored import fg, bg, attr


"""
Self-script which updates your current game playing on Discord as well as an obs.txt output for Text GDI+ on OBS with your current music playing from VLC.
"""

green = fg('#4EC98F')
greenBG = bg('#4EC98F')
magenta = fg('#7D0068')
magentaBG = bg('#7D0068')
yellow = fg('#FFCC00')
yellowBG = bg('#FFCC00')
red = fg('#FF0000')
redBG = bg('#FF0000')
white = fg('#FFFFFF')
whiteBG = bg('#FFFFFF')
blue = fg('#3179B1')
blueBG = bg('#3179B1')
lavender = fg('#A074C4')
lavenderBG = bg('#A074C4')
orange = fg('#E86222')
orangeBG = bg('#E86222')
BOLD = attr('bold')
res = attr('reset')

clientError = False

sys.stdout.write("\x1b];VLC Discord & OBS Now Playing Utility - Notorious Development\x07")

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    running_mode = 'Frozen/executable'
else:
    try:
        app_full_path = os.path.realpath(__file__)
        application_path = os.path.dirname(app_full_path)
        running_mode = "Non-interactive (e.g. 'python myapp.py')"
    except NameError:
        application_path = os.getcwd()
        running_mode = 'Interactive'

os.system('cls' if os.name == 'nt' else 'clear')

if os.name == 'nt':
    application_path = application_path + "\\"
    jfile = application_path + 'settings.json'
else:
    application_path = application_path + "/"
    jfile = application_path + 'settings.json'

if os.path.exists(jfile):
    jdata = json.load(open(jfile))
else:
    jdata = open(jfile, 'w')
    jtmp = '{\n"token\":\"Token_Here\",\n"vlc_password\":\"\"\n}'
    jdata.write(jtmp)
    jdata.close()
    jdata = json.load(open(jfile))

os.environ["rg"] = str(jdata['token'])
token = str(jdata['token'])

if token == "Token_Here":
    token = getpass(f"{res}{lavenderBG}{white}{BOLD}What is your Discord User Authorization Token?:")
    jdata['token'] = str(token)
    with open(jfile, 'w') as outfile:
        json.dump(jdata, outfile)
    

os.environ["rg"] = str(jdata['vlc_password'])
passw = str(jdata['vlc_password'])
if passw == "":
    passw = getpass(f"{res}{orangeBG}{white}{BOLD}What is your VLC WEB Lua password?:") #shhh I know it's insecure
    jdata['vlc_password'] = str(passw)
    print(f'{res}{lavender}{BOLD}------')
    with open(jfile, 'w') as outfile:
        json.dump(jdata, outfile)

bot = commands.Bot(command_prefix='~', description="librarian", pm_help=None, self_bot=True)
 
def convert(seconds): 
    seconds = seconds % (24 * 3600) 
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        return "%02d:%02d" % (minutes, seconds)
    else:
        return "%d:%02d:%02d" % (hour, minutes, seconds)
    
#main async loop 
async def looptons():
    alreadyplaying = ""
    while True:
        alreadyplaying = await updateSong(alreadyplaying)
        await asyncio.sleep(1)
    
@bot.event
async def on_ready():
    print(f'{res}{lavender}{BOLD}Logged in to Discord as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    main_loop = asyncio.get_event_loop()
    main_loop.create_task(looptons()) #start main async loop
    
async def updateSong(alreadyplaying):
    global clientError
    try: #connect to vlc
        s = requests.Session()
        s.auth = ('',passw)
        r = s.get('http://localhost:8080/requests/status.xml', verify=False)
        clientError = False
        if ('401 Client error' in r.text):
            if clientError != True:
                clientError = True
                print(f"{res}{orangeBG}{white}{BOLD}web interface error, do passwords match?")
            return
    except:
        if clientError != True:
            clientError = True
            await bot.change_presence(activity=None)
            print(f"{orangeBG}{white}{BOLD}web interface error: is VLC running? is web interface enabled?")
        return
    artist = ""
    song = ""
    file = ""
    durration = ""
    position = ""
    soup = BeautifulSoup(r.content, 'lxml')
    #print(soup.information)
    durration = soup.find("length")
    position = soup.find("time")
    durration = convert(int(durration.contents[0]))
    #print(durration)
    position = convert(int(position.contents[0]))
    #print(position)
    old_position = ''


    playing = soup.state.text == 'playing' # bool flag
    paused = soup.state.text == 'paused'
    infos = soup.find_all("info")
    for s in infos:
        if s.attrs['name'] == 'title':
            if ' - ' in s.contents[0]:
                artist = s.contents[0].split(' - ')[0]
                song = s.contents[0].split(' - ')[1]
            else:
                song = s.contents[0]
        if s.attrs['name'] == 'filename':
            file = s.contents[0]
        if artist  == "":
            if s.attrs['name'] == 'artist':
                artist = s.contents[0]
    
    if playing and artist != "" and song != "":        
        nowplaying = html.unescape(artist + ' - ' + song) #from web xml so can be escaped
    elif artist == "" and song == "":
        nowplaying = file
    else:
        nowplaying = None


    #obs gdi update
    if nowplaying != None and len(nowplaying) > 2 and position != old_position:
        tailingspaces = ""
        file1 = open(application_path + "obs.txt","w", encoding="utf-8") 
        for chars in range(len(nowplaying) + len(f"({position}/{durration})")):
            tailingspaces = tailingspaces + " "
        file1.write(f"{nowplaying} ({position}/{durration}){tailingspaces}")
        file1.close()
        old_position = position
    else:
        file1 = open(application_path + "obs.txt","w", encoding="utf-8") 
        file1.write('\n')
        file1.close()

    if nowplaying != alreadyplaying and paused == False: #keep the requests to discord server down
        alreadyplaying = nowplaying
        activity = None

        #discord status update
        if nowplaying != None and len(nowplaying) > 2:
            sys.stdout.write("\x1b];"+nowplaying+"\x07") #write song to terminal title
            print(f"{res}{lavenderBG}{white}{BOLD}[✔] Discord Status Updated: {nowplaying} ({durration})")
            activity = discord.Activity(type=discord.ActivityType.playing, name=f"🎶{nowplaying} ({durration})🎶")
        else:
            activity = None
            sys.stdout.write("\x1b];VLC Discord & OBS Now Playing Utility - No Media Currently Playing...\x07")
            print(f"{res}{lavender}{BOLD}[✘] Discord Status Cleared.")
        await bot.change_presence(activity=activity)

    return alreadyplaying
    
@bot.event
async def on_message(message):   
    await bot.process_commands(message) # to the superclass ???
    
bot.run(token, bot=False)