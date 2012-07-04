#!/usr/bin/env python
from csv import reader, writer
from sys import argv, maxint
import nltk
from operator import itemgetter

# TODO
# - create class for entry groups e.g. well-formed entries
# - each subclass has its own processing and output methods
# - base class has driver method

# TODO
# Add unit tests

# function to load up the reference CPEs
# returned as a sorted list of entries, each of which is a python dictionary

def load_reference_cpes():
  dict_reader = reader(open(argv[2],'rb'),delimiter=',') 
  dict_entries = []
  for row in dict_reader:
    cpe_entry = row[1].strip().split(":")
    dict_entry = {
      'cpe'   : ':'.join(cpe_entry[2:]),  # remove the 'cpe:/' prefix
      'name'  : row[0].strip().lower(),   # lowercase the name
      'actual_cpe' : row[1],              # remember the actual cpe
      'actual_name' : row[0]              # and actual name
    }
    dict_entries.append(dict_entry)
  return sorted(dict_entries, key = itemgetter('name'))


# get start and stop points per character in the sorted list of reference cpes
# basically, for a char, say 'g', we want to know the index range where the entries
# starting with 'g' are in the input list

def get_bounds(dict_entries):
  prev = ''
  starts = {}
  stops = {}
  for i in xrange(0,len(dict_entries)):
    c = dict_entries[i]['name'][0]
    if c != prev:
      stops[prev] = i
      starts[c] = i
      prev = c
  
  stops[c] = len(dict_entries)  
  return (starts,stops)
  
  
# load up the database CSV file
# returns 4 sorted lists, each of which contains a subset of the entries

def load_db():
  our_reader = reader(open(argv[1],'rb'),delimiter=',',quotechar='"')
  
  our_entries = []
  any_entries = []
  undef_entries = []
  parse_entries = []
  real_entries_dict = {}
  
  for row in our_reader:
    entry = ':'.join(row).strip().lower()
    real_entries_dict[entry] = row
    version = row[2].upper()
    if version.startswith("ANY") or version.startswith("ALL"):
      any_entries.append(entry)
    elif version.startswith("UNDEF"):
      undef_entries.append(entry)
    elif ">" in version or "<" in version or "=" in version or "-" in version:
      parse_entries.append(entry)
    else:
      our_entries.append(entry)
  return (sorted(our_entries), sorted(any_entries), sorted(undef_entries), sorted(parse_entries),real_entries_dict) 

# function to process a well-formed entry (i.e. one with no wildcards or other
# weird stuff in the version field)

# Algorithm:
# =========
# for each CPE in the supplied range:
#   calculate sum of edit distances of the entry to the CPE and the reference name
#   multiply it by sum of jaccard distances of the entry to the CPE and the reference name
# Return the match with minimum distance, or None if there is no obvious match

def process_wf_entry(entry, dict_entries, start, stop):
  min_dist = maxint
  min_dist_components = []
  best_match = None
  
  our_vendor = entry.split(":")[0]
  our_vendor = ''.join(our_vendor.split())
  
  for i in xrange(start, stop):
    dict_entry = dict_entries[i]
    
    if our_vendor not in ''.join(dict_entry['name']): # heuristic
      continue
    
    d1 = nltk.metrics.edit_distance(entry, dict_entry['cpe'])
    d2 = nltk.metrics.edit_distance(entry, dict_entry['name'])
    d3 = nltk.metrics.jaccard_distance(set(entry), set(dict_entry['cpe']))
    d4 = nltk.metrics.jaccard_distance(set(entry), set(dict_entry['name']))
    
    dist =  (d1+d2)*(d3 + d4)
    
    if dist < min_dist:
      min_dist = dist
      min_dist_components = [d1,d2,d3,d4,dist]
      best_match = dict_entry
  
  return (best_match, min_dist_components)
 

# Main

def main():
  (wf_entries, any_entries, undef_entries, parse_entries,real_entries_dict) = load_db()
    
  print "Total entries:", len(real_entries_dict)
  print "Total well-formed entries:", len(wf_entries)
  
  dict_entries = load_reference_cpes()
  (starts,stops) = get_bounds(dict_entries)
  
  def process_entries(entries_list, entries_func, res_writer):
    matched = 0
    for entry in entries_list:
      try:
        (best_match,min_ds) = entries_func(entry,dict_entries,starts[entry[0]],stops[entry[0]])
      except KeyError:
        best_match = None
      
      if best_match is not None:
        res_row = [' '.join(real_entries_dict[entry]),best_match['actual_cpe'],best_match['actual_name']] + [str(i) for i in min_ds]
        matched += 1
      else:
        res_row = [' '.join(real_entries_dict[entry]),"NA","NA","NA","NA","NA"]
    
      res_writer.writerow(res_row)
    return matched

  with open('output.csv', 'wb') as f:
    res_writer = writer(f)
    matched = process_entries(wf_entries, process_wf_entry, res_writer)   
    print "Total well-formed entries matched:", matched
  
if __name__ == '__main__':
    main()