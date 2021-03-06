import csv
from fuzzywuzzy import fuzz
import time
import datetime
import rdflib
from rdflib import Graph
from rdflib.namespace import RDF, SKOS, DC
from rdflib import URIRef, BNode, Literal
from rdflib.plugins.sparql import prepareQuery
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--rdfFileName', help='the RDF file to be reconciled against (include the extension). optional - if not provided, the script will ask for input')
parser.add_argument('-f', '--fileName', help='the CSV file of headings to reconcile (including \'.csv\'). optional - if not provided, the script will ask for input')
parser.add_argument('-d', '--directory', help='the directory for the input and output files. optional - if not provided, the script will assume null')
parser.add_argument('-t', '--threshold', help='the threshold (e.g. \'90\' means the strings are 90% similar and 10% different ). optional - if not provided, the script will default to 70')
args = parser.parse_args()

if args.rdfFileName:
    rdfFileName = args.rdfFileName
else:
    rdfFileName = raw_input('Enter the RDF file to be reconciled against (include the extension): ')
if args.fileName:
    fileName = args.fileName
else:
    fileName = raw_input('Enter the CSV file of headings to reconcile (including \'.csv\'): ')
if args.threshold:
    threshold = int(args.threshold)
else:
    threshold = 70
if args.directory:
    directory = args.directory
else:
    directory = ''

#define function for finding the prefLabel of a subject
def retrievePrefLabel(uri):
    q = prepareQuery('SELECT ?o ?d WHERE {?s skos:prefLabel ?o. ?s dc:date ?d. }', initNs = {'skos': SKOS, 'dc': DC})
    results = g.query(q, initBindings={'s': URIRef(uri)})
    for row in results:
        prefLabel = row[0].encode('utf-8')
        date = row[1]
    global match
    match = [label, str(prefLabel), uri, date]

os.chdir(directory)
startTime = time.time()
date = datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')

#import rdf file into graph
g = Graph()
g.parse(rdfFileName, format='n3')
g.bind('skos', SKOS)

#create dict of pref and alt labels from rdf file
existingLabels = {}
q = prepareQuery('SELECT ?s ?o WHERE { ?s skos:prefLabel|skos:altLabel ?o }', initNs = {'skos': SKOS})
results = g.query(q)
for row in results:
    existingLabels[str(row[1].encode('utf-8'))] = str(row[0])

#create lists and csv files
completeNearMatches = []
completeExactMatches = []
f=csv.writer(open(os.path.join('reconciliationResults','rdfExactMatches'+date+'.csv'),'wb'))
f.writerow(['originalLabel']+['standardizedLabel']+['uri']+['date'])
f2=csv.writer(open(os.path.join('reconciliationResults','rdfNearAndNonMatches'+date+'.csv'),'wb'))
f2.writerow(['originalLabel']+['standardizedLabel']+['uri']+['date'])

#create counters
newHeadingsCount = 0
exactMatchNewHeadings = 0
nearMatchNewHeadings = 0
nonmatchedNewHeadings = 0

#parse CSV data and compares against existingLabels dict for exact and near matches
with open(fileName) as csvfile:
    reader = csv.DictReader(csvfile)
    rowCount = len(list(reader))
with open(fileName) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        label = row['name']
        rowCount -= 1
        print 'Rows remaining: ', rowCount
        newHeadingsCount += 1
        preCount = len(completeNearMatches)
        for label2, uri in existingLabels.items():
            if label == label2:
                exactMatchNewHeadings += 1
                completeExactMatches.append(label)
                retrievePrefLabel(uri)
                f.writerow([match[0]]+[match[1]]+[match[2]]+[match[3]])
        if label not in completeExactMatches:
            for label2, uri in existingLabels.items():
                ratio = fuzz.ratio(label, label2)
                partialRatio = fuzz.partial_ratio(label, label2)
                tokenSort = fuzz.token_sort_ratio(label, label2)
                tokenSet = fuzz.token_set_ratio(label, label2)
                avg = (ratio+partialRatio+tokenSort+tokenSet)/4
                if avg > threshold:
                    retrievePrefLabel(uri)
                    if match not in completeNearMatches:
                        completeNearMatches.append(match)
                postCount = len(completeNearMatches)
            if postCount > preCount:
                nearMatchNewHeadings += 1
            else:
                nonmatchedNewHeadings += 1
                f2.writerow([label]+['']+['no match']+[''])

#write results to CSV file
for match in completeNearMatches:
    f2.writerow([match[0]]+[match[1]]+[match[2]]+[match[3]])

print 'Total headings reconciled: ', newHeadingsCount
print 'Exact match headings: ', exactMatchNewHeadings
print 'Near match headings: ', nearMatchNewHeadings
print 'Unmatched headings: ', nonmatchedNewHeadings

elapsedTime = time.time() - startTime
m, s = divmod(elapsedTime, 60)
h, m = divmod(m, 60)
print 'Total script run time: ', '%d:%02d:%02d' % (h, m, s)
