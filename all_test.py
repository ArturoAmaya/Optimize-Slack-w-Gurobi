import chat_optimize
import curricularanalytics as ca
from curricularanalytics import Curriculum, DegreePlan
import os
import pandas as pd
import re
import urllib
import traceback

def urlize(dp:DegreePlan, college: str, major:str, year:int, optimized: bool):
    c = ca.write_csv(dp) # if you don't say where it writes to string
    d = re.sub('"([a-z, A-Z,0-9]+[\/,0-9,A-Z, ]+)"', r'\1', c.getvalue())
    shard = urllib.parse.quote(re.sub('"(([0-9]+;?)*)"', r'\1', d), safe='()/')
    # new content in the url includes year, major code, title
    title = f"&title={major}+({college},+{year}):+{(dp.curriculum.name).replace(' ', '+')}+{'Optimized' if optimized else 'Unoptimized'}"
    year = f"&year={year}"
    major = f"&major={major}"
    #title = f"&title={major}+({college},+{2024}):+{(dp.curriculum.name).replace(' ', '+')}"
    #&year=2024&major=PB31&title=PB31+(Revelle,+2024):+Public+Health+with+Concentration+in+Medicine+Sciences
    dp_url = "https://educationalinnovation.ucsd.edu/_files/graph-demo.html?defaults=ucsd" + year + major + title + "#" + shard
    return dp_url
                

def slack_calc(dp:DegreePlan):
    slack = 0
    for term_index, term in enumerate(dp.terms):
        for course in term.courses:
            for prereq in course.requisites:
                prereq_course = [dp.terms.index(t) for t in dp.terms for c in t.courses if c.id == prereq]
                slack += term_index - prereq_course[0]

    return slack

def slack_list(dp:DegreePlan):
    ret = []
    for term_index, term in enumerate(dp.terms):
        for course in term.courses:
            course_slack = 0
            for prereq in course.requisites:
                prereq_course = [dp.terms.index(t) for t in dp.terms for c in t.courses if c.id == prereq]
                course_slack += term_index - prereq_course[0]
                ret.append((course_slack, course.id))
    return ret

def find_isolates(dp: DegreePlan):
    isolates = {}
    for term_index, term in enumerate(dp.terms):
        for course in term.courses:
            if not course.requisites: #i.e. it has no prereqs

                # look through all the courses and check whether they depend on me
                courses_that_depend_on_me = []
                # look through all courses in curriculum. if one of them lists me as a prereq, add them to the list
                for dep_course in dp.curriculum.courses:
                    # look through the courses prerequisite
                    for key in dep_course.requisites:
                        # the key is what matters, it is the id of the course in the curriculum
                        if (key == course.id):  # let's skip co-reqs for now... interesting to see if this matters later. It does! see MATH 20B of BE25 in the sample data
                            courses_that_depend_on_me.append(course)
                if not courses_that_depend_on_me:
                    # it's isolated now
                    isolates[str(course.id)] = term_index
            else:
                continue
    return isolates

def find_non_isolates(dp: DegreePlan):
    isolates = {}
    non_isolates = {}
    for term_index, term in enumerate(dp.terms):
        for course in term.courses:
            if not course.requisites: #i.e. it has no prereqs

                # look through all the courses and check whether they depend on me
                courses_that_depend_on_me = []
                # look through all courses in curriculum. if one of them lists me as a prereq, add them to the list
                for dep_course in dp.curriculum.courses:
                    # look through the courses prerequisite
                    for key in dep_course.requisites:
                        # the key is what matters, it is the id of the course in the curriculum
                        if (key == course.id):  # let's skip co-reqs for now... interesting to see if this matters later. It does! see MATH 20B of BE25 in the sample data
                            courses_that_depend_on_me.append(course)
                if not courses_that_depend_on_me:
                    # it's isolated now
                    isolates[str(course.id)] = term_index
                else:
                    non_isolates[str(course.id)] = (max(0,term_index-5), min(term_index+5, 11))
            else:
                non_isolates[str(course.id)] = (max(0,term_index-5), min(term_index+5, 11)) # HARDCODED
    return (isolates, non_isolates)


results = {}
df = pd.DataFrame(columns=['Major', 'College', 'Original Slack', 'New Slack', 'Difference', 'Old Avg Slack', 'New Avg Slack', 'Old Avg Slack w/ Zeros', 'New Avg Slack w/ Zeros', 'Old Max', 'New Max', 'Old Min', 'New Min', 'Old URL', 'New URL'])
for dirpath, dirnames, filenames in os.walk("../../WhatIfSite/WhatIfSite/app/infrastructure/files/output"):
    for dirname in dirnames: 
        if not os.path.exists('./opt_results/' + dirname):
            os.makedirs('./opt_results/' + dirname)
    for filename in filenames:
        if filename.endswith('.csv'):
            #print(os.path.join(dirpath, filename))
            output_dir = os.path.join(dirpath, filename).replace("../../WhatIfSite/WhatIfSite/app/infrastructure/files/output", "")
            try:
                dp = ca.read_csv(os.path.join(dirpath, filename))
                if type(dp) == DegreePlan:
                    curr = dp.curriculum
                    term_count = 12
                    min_cpt = 12
                    max_cpt = 18
                    obj_order = ['Prereq']#, 'Balance'] # for now just do 'prereq' and don't include 'balance'. Seems balance without specifying that lower divs should be taken earlier leads to final quarter CSE 30 or something in MA30/RE (to have an example)
                    # the no more than 20 units per quarter should be a sufficient barrier. TODO: look into providing more infot to the tool like MATH 20A range 0-3 or something like that

                    #fixed_courses = find_isolates(dp)#{'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}# This has a very easy solve the other don't for some reason {'32': 5, '33': 7, '34': 9, '35': 10, '36': 11} ##{'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}
#term_range = {'37': (5,11), '38': (5,11), '39': (5,11), '40': (5,11), '41': (5,11)} #Dict(Int, (Int, Int))` : specify courses that should appear in a particular range of terms in `(course_id, (low_range, high_range))` format.
                    (fixed_courses, ranged_courses) = find_non_isolates(dp) 

                    opt = chat_optimize.optimize_plan(curr, term_count, min_cpt, max_cpt, obj_order, "", {}, fixed_courses, {}, {}, [])
                    ca.write_csv(opt, f'./opt_results/{output_dir}' )

                    # also make a url for it
                    #c = ca.write_csv(opt) # if you don't say where it writes to string
                    #d = re.sub('"([a-z, A-Z,0-9]+[\/,0-9,A-Z, ]+)"', r'\1', c.getvalue())
                    #shard = urllib.parse.quote(re.sub('"(([0-9]+;?)*)"', r'\1', d), safe='()/')
                    #dp_url = "https://educationalinnovation.ucsd.edu/_files/graph-demo.html?defaults=ca#" + shard
                
                    results[output_dir.replace("/", "")] = {'original': slack_calc(dp), 'new': slack_calc(opt), 'difference':  slack_calc(dp) - slack_calc(opt)}

                    df.loc[len(df)] = {
                        'Major': output_dir.replace("/", "")[0:-6], 
                        'College': output_dir.replace("/", "")[-6:-4], 
                        'Original Slack': slack_calc(dp), 
                        'New Slack': slack_calc(opt), 
                        'Difference': slack_calc(opt)-slack_calc(dp),
                        'Old Avg Slack': slack_calc(dp)/(len(dp.curriculum.courses)-len(find_non_isolates(dp))),
                        'New Avg Slack': slack_calc(opt)/(len(opt.curriculum.courses)-len(find_non_isolates(opt))),
                        'Old Avg Slack w/ Zeros': slack_calc(dp)/len(dp.curriculum.courses),
                        'New Avg Slack w/ Zeros': slack_calc(opt)/len(opt.curriculum.courses),
                        'Old Max': max([x[0] for x in slack_list(dp)]), 
                        'New Max': max(x[0] for x in slack_list(opt)), 
                        'Old Min': min([x[0] for x in slack_list(dp)]), 
                        'New Min': min([x[0] for x in slack_list(opt)]),
                        'Old URL': urlize(dp, output_dir.replace("/", "")[-6:-4], output_dir.replace("/", "")[0:-6], 2024, False), 
                        'New URL': urlize(opt, output_dir.replace("/", "")[-6:-4], output_dir.replace("/", "")[0:-6], 2024, True), 
                        }


            except:
                print(traceback.format_exc())
                results[output_dir] = {'original': 0, 'new': 0, 'difference':  0}
                # use the old vcalues
                if type(dp) == DegreePlan:
                    df.loc[len(df)] = {
                    'Major': output_dir.replace("/", "")[0:-6], 
                        'College': output_dir.replace("/", "")[-6:-4], 
                        'Original Slack': slack_calc(dp), 
                        'New Slack': slack_calc(dp), 
                        'Difference': 0,
                        'Old Avg Slack': slack_calc(dp)/(len(dp.curriculum.courses)-len(find_non_isolates(dp))),
                        'New Avg Slack': slack_calc(dp)/(len(dp.curriculum.courses)-len(find_non_isolates(dp))),
                        'Old Avg Slack w/ Zeros': slack_calc(dp)/len(dp.curriculum.courses),
                        'New Avg Slack w/ Zeros': slack_calc(dp)/len(dp.curriculum.courses),
                        'Old Max': max([x[0] for x in slack_list(dp)]), 
                        'New Max': max(x[0] for x in slack_list(dp)), 
                        'Old Min': min([x[0] for x in slack_list(dp)]), 
                        'New Min': min([x[0] for x in slack_list(dp)]),
                        'Old URL': urlize(dp, output_dir.replace("/", "")[-6:-4], output_dir.replace("/", "")[0:-6], 2024, False), 
                        'New URL': '' #urlize(opt, output_dir.replace("/", "")[-6:-4], output_dir.replace("/", "")[0:-6], 2024, True), 
                    }
        df.to_csv("results_2024.csv")
print(results)

import json 
  
with open('convert_2024.json', 'w') as convert_file: 
     convert_file.write(json.dumps(results, sort_keys = True, indent=1))