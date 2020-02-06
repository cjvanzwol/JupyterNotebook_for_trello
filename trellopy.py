#!/usr/bin/env python
# coding: utf-8

# ## Import libraries

# In[ ]:


import requests,json,os, pprint,requests
import pandas as pd
from datetime import date,datetime,timedelta


# ### Load configuration and credentials

# In[ ]:


if os.path.exists('configuration.txt'):
    with open('configuration.txt') as json_file:
        config = json.load(json_file)
else:
    print('No configuration found. To create one, run Setup!')

if os.path.exists('credentials.txt'):
    with open('credentials.txt') as json_file:
        credentials = json.load(json_file)
else:
    print('No credentials found. To create one, run Setup!')


# ### Create URLs

# In[ ]:


keys = "key="+credentials.get('api_key')+"&token="+credentials.get('api_token')
trello_base_url = "https://api.trello.com/1/"
board_url = trello_base_url+"boards/"+config.get('boardid')
url_cards = board_url+"/cards?attachments=true&customFieldItems=true&filter=all&"+keys
url_lists = board_url+"/lists?filter=all&"+keys
url_customfields = board_url+"/customFields?"+keys
url_labels = board_url+"/labels?"+keys
url_members = board_url+"/members?"+keys


# ### Get the JSON objects and parse them

# In[ ]:


cards = json.loads(json.dumps(requests.get(url_cards).json()))
lists = json.loads(json.dumps(requests.get(url_lists).json()))
customfields = json.loads(json.dumps(requests.get(url_customfields).json()))
labels = json.loads(json.dumps(requests.get(url_labels).json()))
members = json.loads(json.dumps(requests.get(url_members).json()))


# ### Create dictionary for custom fields (if exists)

# In[ ]:


customfields_dict = {}
for i in customfields:
    customfields_dict[i['id']] = {}
    if i['type'] == 'date':
        customfields_dict[i['id']][i['name']] = {}
        customfields_dict[i['id']][i['name']]['options'] = {'id': 'date'}


    else:
        customfields_dict[i['id']][i['name']] = {}
        customfields_dict[i['id']][i['name']]['options'] = {}
        for j in i['options']:
            customfields_dict[i['id']][i['name']]['options'][j['id']] =  j['value']['text']


# ### If there are custom fields with dates, treat them differently

# In[ ]:


customfieldsmetdate = []
for i,j in customfields_dict.items():
        for k,l in j.items():
            try:
                if l['options']['id'] == 'date':
                    customfieldsmetdate.append(i)
            except:
                pass


# ## Create a list for all the chosen lists in the configuration

# In[ ]:


chosenlists = []
for i in config.get('notstarted'):
    chosenlists.append(i)
chosenlists.extend(config.get('blocked'))
chosenlists.extend(config.get('doing'))
chosenlists.extend(config.get('done'))


# ### Create function to get the hashed date from the card ID

# In[ ]:


def idtodate(cardid):
    hex = cardid[0:8]
    timestamp = int(hex,16)
    timedate = datetime.fromtimestamp(timestamp)
    return timedate


# ### Create dictionary with all cards

# In[ ]:


kaarten = {}
for i in cards:
    kaarten[i['id']] = {'name': i['name'],
                        'cardid': i['id'],
                        'idlist': i['idList'],
                        'customfields': i['customFieldItems'],
                        'labels': {},
                        'members': {},
                        'sjabloon': i['isTemplate'],
                        'due': None,
                        'closed': i['closed'],
                        'attachments': {},
                        'shortUrl': i['shortUrl']
                       }
    for j in i['idMembers']:

        for k in members:

            if j == k['id']:
                    kaarten[i['id']]['members'][k['id']] = k['fullName']
    if i['due'] != None:
        kaarten[i['id']]['due'] = datetime.strptime(i['due'][0:19],'%Y-%m-%dT%H:%M:%S')
    for j in i['labels']:
        kaarten[i['id']]['labels'][j['id']] = j['name']
    for j in i['attachments']:
        try:
            if j['url'][0:21]== 'https://trello.com/c/':
                kaarten[i['id']]['attachments'][j['url'][21:29]] = None
        except:
            pass


# ### Add custom fields if they exist

# In[ ]:


if customfields_dict != {}:
    for i,j in customfields_dict.items():
        for k,l in j.items():
            for m,n in kaarten.items():
                n[k] = None

    for i,j in kaarten.items():
        for k in j['customfields']:
            if k['idCustomField'] in customfieldsmetdate:
                for l,m in customfields_dict.items():
                    for n,o in m.items():
                        if k['idCustomField'] == l:
                            j[n] = datetime.strptime(k['value']['date'][0:19],'%Y-%m-%dT%H:%M:%S')
            else:
                for l,m in customfields_dict.items():
                    for n,o in m.items():
                        if k['idCustomField'] == l:
                            for p,q in o.items():
                                for r,s in q.items():
                                    if k['idValue'] == r:
                                        j[n] = s


# ### Add the statuses (Not started, Doing, Blocked and Done), based on the configuration

# In[ ]:


for i,j in kaarten.items():
    date = idtodate(i)
    j['created'] = date
    for k in lists:
        if j['idlist'] == k['id']: j['list'] = k['name']
    if j['list'] in config.get('notstarted'):
        j['status'] = 'Not started'
    elif j['list'] in config.get('doing'):
        j['status'] = 'Doing'
    elif j['list'] in config.get('blocked'):
        j['status'] = 'Blocked'
    elif j['list'] in config.get('done'):
        j['status'] = 'Done'
    else:
        j['status'] = 'Archived'
    del j['customfields']
    del j['idlist']


# ### Give the status Archived if the card is closed and not done

# In[ ]:


for i,j in kaarten.items():
    if j['closed'] == True and j['status'] != 'Done':
        j['status'] = 'Archived'


# ### Create object with lists that are not chosen

# In[ ]:


liststodelete = []
for i in lists:
    if i['name'] not in chosenlists:
        liststodelete.append(i['name'])


# ### Create object with all cards that should be deleted (ignored)

# In[ ]:


cardstodelete = []
for i,j in kaarten.items():
    if j['sjabloon'] == True:
        cardstodelete.append(i)
    elif j['list'] in liststodelete:
        cardstodelete.append(i)


# ### Delete the cards in the object 'cardstodelete'

# In[ ]:


for i in cardstodelete:
    if i in kaarten:
        del kaarten[i]


# ### Create function to get all actions from a card

# In[ ]:


def actions_card(idofcard):
    objectname = json.loads(json.dumps(requests.get(trello_base_url+"cards/"+idofcard+"/actions?actions_limit=1000&"+keys).json()))
    return objectname


# ### Get the actions from all cards

# In[ ]:


for i,j in kaarten.items():
    j['actions'] = actions_card(i)


# ### Create function to convert the JSON Time in string format to DateTime

# In[ ]:


def dateCalc(date):
    newdate = datetime.strptime(date[0:19],'%Y-%m-%dT%H:%M:%S')
    return newdate


# ### Get all list movements of all cards

# In[ ]:


for i,j in kaarten.items():
    j['listmovements'] = {}
    for k in j['actions']:
        for l,m in k.items():
            try:
                j['listmovements'][dateCalc(k['date'])] = {'listAfter': k['data']['listAfter']['id'], 'listBefore': k['data']['listBefore']['id']}
            except:
                pass


# ### Determine the right list movements with date and time (including the fist list)

# In[ ]:


for i,j in kaarten.items():
    j['movements'] = {}
    if j['listmovements'] == {}:
        j['movements'][j['created']] = {'listBefore': None, 'listAfter': j['list']}
    else:
        tmpdates = []
        for k,l in j['listmovements'].items():
            tmpdates.append(k)
        for m in tmpdates:
            for n,o in j['listmovements'].items():
                if n == m:
                    j['movements'][m] = {'listAfter': o['listAfter'],'listBefore': o['listBefore']}
        for k,l in j['listmovements'].items():
            if k == min(tmpdates):
                j['movements'][j['created']] = {'listBefore': None, 'listAfter': l['listBefore']}

for i,j in kaarten.items():
    del j['actions']


# ### Because listnames could be changed, the list ID was added in previous commands. With this code, the current listname is displayed

# In[ ]:


historicallists = []
historicallists.extend(chosenlists)

for i,j in kaarten.items():
    for k,l in j['movements'].items():
        for m,n in l.items():
            for o in lists:
                if o['id'] == n:
                    l[m] = o['name']
                    historicallists.append(o['name'])


# ### Create a dictionary with date-keys (past 400 days)

# In[ ]:


datesdict = {}
now = datetime.now().date()
numdays = 400

for x in range (0, numdays):
    datesdict[str(now - timedelta(days = x))] = {}


# ### Determine how many cards were in what list on the dates in the Dates-dictionary

# In[ ]:


for i,j in datesdict.items():
    datekey = datetime.strptime(i,'%Y-%m-%d').date()
    for k in historicallists:
        j[k] = 0
    for l,m in kaarten.items():
        if m['list'] in chosenlists:
            if m['status'] != 'Archived':
                for n,o in m['movements'].items():
                    if n.date() <= datekey <= now:
                        if o['listBefore'] != None:
                            j[o['listBefore']] -= 1
                            j[o['listAfter']] += 1
                        else:
                            j[o['listAfter']] += 1


# ### If all values are zero for a date, that date is useless, so deleting..

# In[ ]:


for i,j in kaarten.items():
    j['datedone'] = None
    j['datestarted'] = None
    j['datelastblocked'] = None
    j['datelastunblocked'] = None

    if j['status'] == 'Done':
        tmp = []
        for k,l in j['movements'].items():
            if l['listAfter'] in config['done']:
                tmp.append(k)
        j['datedone'] = max(tmp)

    if j['status'] != 'Done' or 'Archived':
        tmp = []
        for k,l in j['movements'].items():
            if l['listAfter'] in config['doing']:
                tmp.append(k)
        if tmp != []:
            j['datestarted'] = min(tmp)

    if j['datestarted'] == None:
        if j['status'] != 'Archived':
            if j['status'] != 'Not started':
                j['datestarted'] = j['created']
    tmp = []
    if j['status'] != 'Blocked':
        for k,l in j['movements'].items():
            if l['listBefore'] in config['blocked']:
                tmp.append(k)
                j['datelastunblocked'] = max(tmp)
    tmp = []
    for k,l in j['movements'].items():
        if l['listAfter'] in config['blocked']:
            tmp.append(k)
            j['datelastblocked'] = max(tmp)


# ### Create a temporary list with all dates from the Dates dictionary

# In[ ]:


datelist = []
for i in datesdict.keys():
    datelist.append(i)


# ### Create a dictionary for in and out and determine values with dates already in the cards dictionary

# In[ ]:


in_out = {}
for i in datelist:
    in_out[i]= {}
for i,j in in_out.items():
    j['In'] = 0
    j['Out'] = 0
    for k,l in kaarten.items():
        for m,n in l.items():
            x = 0
            y = 0
            if m=='created':
                if i==str(n)[0:10]:
                    x += 1
                    j['In'] += 1
            if m=='datedone':
                if i==str(n)[0:10]:
                    y += 1
                    j['Out'] += 1
for i,j in in_out.items():
    i = datetime.strptime(i,'%Y-%m-%d')
for i,j in datesdict.items():
    for k,l in in_out.items():
        if i==k:
            j['In'] = l['In']
            j['Out'] = l['Out']


# ### Create function to ouput all cards to excel

# In[ ]:


def excelalldata():
    import pandas as pd
    labelslist = []
    for i,j in kaarten.items():
        for k,l in j.items():
            if k=='labels' and l != {}:
                for m,n in l.items():
                    labelslist.append((i,n))
    memberslist = []
    for i,j in kaarten.items():
        for k,l in j.items():
            if k=='members' and l !={}:
                for m,n in l.items():
                    memberslist.append((i,n))
    if labelslist != []:
        columnslabels = ['cardid','label']
        columnsmembers = ['cardid','member']
        df1 = pd.DataFrame(data=kaarten).T
        df2 = pd.DataFrame(data=labelslist,columns=columnslabels)
        df3 = pd.merge(df1,df2,on='cardid', how='left')
        df4 = pd.DataFrame(data=memberslist,columns=columnsmembers)
        df5 = pd.merge(df3,df4,on='cardid', how='left')
        df5.to_excel(config.get('excelfile'))
    else:
        columnsmembers = ['cardid','member']
        df1 = pd.DataFrame(data=kaarten).T
        df2 = pd.DataFrame(data=memberslist,columns=columnsmembers)
        df3 = pd.merge(df1,df2,on='cardid', how='left')
        df3.to_excel(config.get('excelfile'))


# ### Create function to output the timeline to excel (WIP)

# In[ ]:


def exceltimeline():
    print('exceltimeline is not defined yet.')


# ### Create function to output the timeline to Google Sheets

# In[ ]:


def timelinetosheets(dictionary,sheetid,worksheet):
    import gspread
    from df2gspread import df2gspread as d2g
    import oauth2client
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    gcredentials = ServiceAccountCredentials.from_json_keyfile_name(config['jsonfilefromgoogle'] , scope)

    client = gspread.authorize(gcredentials)
    wks = client.open_by_key(sheetid)
    x = 0
    sheetnames = []
    try:
        while wks.get_worksheet(x) != None:
            sheetnames.append(wks.get_worksheet(x).title)
            x += 1
    except:
        pass
    if not worksheet in sheetnames:
        tempwks = wks.add_worksheet(title=worksheet, rows="1000", cols="30")

    dataframe = pd.DataFrame(data=dictionary).T
    d2g.upload(dataframe, sheetid, worksheet, credentials=gcredentials, row_names=True)
    sheet = wks.worksheet(worksheet)
    sheet.update_acell('A1', 'Date')


# ### Create function to output all data to Google Sheets

# In[ ]:


def alldatatosheets(dictionary,sheetid,worksheet):
    import gspread
    from df2gspread import df2gspread as d2g
    import oauth2client
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    gcredentials = ServiceAccountCredentials.from_json_keyfile_name(config['jsonfilefromgoogle'] , scope)

    client = gspread.authorize(gcredentials)
    wks = client.open_by_key(sheetid)
    x = 0
    sheetnames = []
    try:
        while wks.get_worksheet(x) != None:
            sheetnames.append(wks.get_worksheet(x).title)
            x += 1
    except:
        pass
    if not worksheet in sheetnames:
        tempwks = wks.add_worksheet(title=worksheet, rows="1000", cols="30")

    labelslist = []
    for i,j in dictionary.items():
        for k,l in j.items():
            if k=='labels' and l != {}:
                for m,n in l.items():
                    labelslist.append((i,n))
    memberslist = []
    for i,j in dictionary.items():
        for k,l in j.items():
            if k=='members' and l !={}:
                for m,n in l.items():
                    memberslist.append((i,n))
    for i,j in dictionary.items():
        try:
            del j['members']
        except:
            pass
        try:
            del j['labels']
        except:
            pass
    if labelslist != []:
        columnslabels = ['cardid','label']
        columnsmembers = ['cardid','member']
        df1 = pd.DataFrame(data=kaarten).T
        df2 = pd.DataFrame(data=labelslist,columns=columnslabels)
        df3 = pd.merge(df1,df2,on='cardid', how='left')
        df4 = pd.DataFrame(data=memberslist,columns=columnsmembers)
        dataframe = pd.merge(df3,df4,on='cardid', how='left')


    else:
        columnsmembers = ['cardid','member']
        df1 = pd.DataFrame(data=kaarten).T
        df2 = pd.DataFrame(data=memberslist,columns=columnsmembers)
        dataframe = pd.merge(df1,df2,on='cardid', how='left')

    d2g.upload(dataframe, sheetid, worksheet, credentials=gcredentials, row_names=True)


# ### Run all function with value True in the configuration

# In[ ]:


if config['scriptoptions']['excelalldata'] == True:
    print('Not scripted yet.')
#    excelalldata()
if config['scriptoptions']['exceltimeline'] == True:
    print('Not scripted yet.')    
#    exceltimeline()
if config['scriptoptions']['gspreadalldata'] == True:
    alldatatosheets(kaarten,config['spreadsheetid'],config['alldatasheet'])
if config['scriptoptions']['gspreadtimeline'] == True:
    timelinetosheets(datesdict,config['spreadsheetid'],config['timelinesheet'])
if config['scriptoptions']['cleandonelists'] == True:
    print('Not scripted yet.')
#    cleandonelists()
