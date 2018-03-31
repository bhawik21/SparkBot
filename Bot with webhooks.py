# -*- coding: utf-8 -*-
"""
@author: bhraja
"""
import requests
from datetime import datetime
import json

BOT_BEARER = <Your Bot Token Here>
LOG_FILE = <Log File Path Here>
BOT_EMAIL = <Your Bot's Email address Here>

#Function to do the logging
def dumplog(email,text):
    print(text)
    now = datetime.utcnow() #Timestamp in UTC
    log_text = '\n{}  {}  {}'.format(now,email,text)
    with open(LOG_FILE, "a") as myfile:
        myfile.write(log_text)
    return
    

#write back to spark
def postmessage(roomid, botbearer, msgtext):
    url="https://api.ciscospark.com/v1/messages/"
    
    headers = {"Authorization": "Bearer " + botbearer,
               "Content-type":"application/json",
               "charset":"utf-16"}
    payload="{"+"\"" + "roomId" + "\"" + ":" + "\"" + roomid + "\"" + "," + "\"" + "html" + "\"" + ":" +"\""+ msgtext + "\"" + "," + "\"" + "text" + "\"" + ":" +"\""+ msgtext + "\""+"}"
    response = requests.request("POST", url, data=payload, headers=headers)
    return
    

#Read messages typed into Spark
def getmessage(roomid, botbearer):
    url="https://api.ciscospark.com/v1/messages?roomId="+roomid
    headers = {"Authorization": "Bearer " + botbearer,
               "Content-type":"application/json",
               "charset":"utf-8"}
    payload="{"+"\"" + "max" + "\"" + ":" + "\"" + "1" + "\"" +"}"
    response = requests.request("GET", url, data=payload, headers=headers)
    
    result=json.loads(response.text)
    msgtext=[]
    for msg in result['items']:
        msgtext.append(msg['text'])
    return (msgtext[0])
    

import os
from nltk.parse.stanford import StanfordDependencyParser   #This is in case you are doing NLP Dependency Parsing
from nltk import word_tokenize, pos_tag
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import csv

path = <Set Stanford Core NLP Path Here>'   # Set this to where you have downloaded the JAR file to
path_to_jar = path + 'stanford-corenlp-3.9.0.jar'
path_to_models_jar = path + 'stanford-corenlp-3.9.0-models.jar'

dependency_parser = StanfordDependencyParser(path_to_jar=path_to_jar, path_to_models_jar=path_to_models_jar)
os.environ['JAVAHOME'] = <Your JDK Path>  # Set this to where the JDK is


import re
regexpSubj = re.compile(r'subj')
regexpObj = re.compile(r'obj')
regexNouns = re.compile("^N.*|^PR.*")

#Function to build the dependency tree
def get_compounds(triples, word):
    compound = []
    for t in triples:
        if t[0][0] == word:
            if regexNouns.search(t[2][1]):
                compound.append(t[2][0].strip("[]"))
    return compound

#Function to calculate how many keywords matched in a sentence. returns the highest weight


#Function to build keywod list and perform search to return matching sentence in CSV file
def get_response(sentence):
    
    stopWords = set(stopwords.words('english'))
    result = dependency_parser.raw_parse(sentence) #simply returns the list iterator object address of the dependency graph
    dep = next(result)
    
    #discover topic
    root = [dep.root["word"]]
    root.append(get_compounds(dep.triples(), root))
    
    subj = []
    obj = []
    nouns = []
    searchstr=[]   #search keyword list
    
    #discover nouns    
    tokens = word_tokenize(sentence)
    tags=pos_tag(tokens)
    #print(tags)
    for word,tag in tags:
        if tag.startswith('NN') or tag.startswith('JJ') or tag.startswith('VB'):   #noun and adjectives that describe the noun
            nouns.append(word)
       
    #append nouns    
    for p in nouns:
        searchstr.append(str(p).strip('[]'))
    
    
    #discover subject       
    for t in dep.triples():
        if regexpSubj.search(t[1]):
            subj.append(t[2][0])
            subj.append(get_compounds(dep.triples(),t[2][0]))
      
    #append subject    
    for p in subj:
        if type(p)==list:
            for q in p:
                searchstr.append(str(q).strip('[]'))
            continue
        searchstr.append(str(p).strip('[]'))
    
    
   #discover object     
    for t in dep.triples():
        if regexpObj.search(t[1]):
            obj.append(t[2][0])
            obj.append(get_compounds(dep.triples(),t[2][0]))
    
    #append object
    for p in obj:
        if type(p)==list:
            for q in p:
                searchstr.append(str(q).strip('[]'))
            continue
        searchstr.append(str(p).strip('[]'))
    
    
    #append topic    
    for p in root:
        if type(p)==list:
            for q in p:
                searchstr.append(str(q).strip('[]'))
            continue
        searchstr.append(str(p).strip('[]'))
    
    #delete stopwords
    strsrch=[w for w in searchstr if not w in stopWords]
    
    
    #I have a company specific de-jargoning dictionary function here
    
    #Lemmatize the word list
    searchstrings=[]
    lemmatizer_output=WordNetLemmatizer()
    for word in strsrch:
        checklist=[lemmatizer_output.lemmatize(word,'v'), lemmatizer_output.lemmatize(word,'n'), lemmatizer_output.lemmatize(word,'a')]
        searchstrings.append(most_common(checklist))
    
    #remove duplicates by converting into set and back to list
    searchstrings=list(set(searchstrings))
    print("searchstrings=",searchstrings)            
            
    #In my originalcode, I search a knowledge base to retrieve information based on the searchstrings     
    
    return searchstrings;    #the retrieved answer 

#
### Decode messageid into actual text got from webhook
#
def decodemsg(msgid):
    url="https://api.ciscospark.com/v1/messages/"+msgid
    headers = {"Authorization": "Bearer " + BOT_BEARER,
               "Content-type":"application/json",
               "charset":"utf-8"}
    payload="{}"
    response = requests.request("GET", url, data=payload, headers=headers)
    text=json.loads(response.text)
    #print(text)
    return text['text'] 


#Flask approach using webhooks
from flask import Flask, request

app = Flask(__name__)     #Instantiate

#Note: NGROK utility to expose localhost port 5000 as the webserver. 5000 because Flask by default runs on 5000. 

@app.route('/',methods=['POST'])    #Re-Define the POST method
def index():
    webhook=request.get_json()
    #print("Raw webhook data=",webhook)
    
    fromemail=webhook['data']['personEmail']
    msgtype=webhook['resource']          #whether is is somoene adding the bot into a room or asking a question
    roomid=webhook['data']['roomId']     # which room should the answer go to
    question=decodemsg(webhook['data']['id'])  #question being asked by user
    if (fromemail!=BOT_EMAIL):				#So that bot does not read it's own messages and start processing them
        dumplog(fromemail,question)
        if(msgtype=="memberships"):   #If newly created room, then greeting message
            postmessage(roomid,BOT_BEARER,"Welcome, I am the C-Worker Helper Bot! Ask questions in English.")
        else:
            response=get_response(question)
            response=response.replace(u'\xa0', u' ').replace(u'\n', u'-').replace(u'\'',u'')
            dumplog("Bot Ans:",response)
            postmessage(roomid,BOT_BEARER,response)  
    return json.dumps(request.json)

#Run Flask on Localhost as noarguments means on localhost at port 5000    
if __name__ == '__main__':
    app.run('gpe-ops.cisco.com',5000,True)     #Default args missing makes it run on locahost. Actual format is app.run(host='0.0.0.0', port=port, debug=True)