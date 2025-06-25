import chat_optimize
import curricularanalytics as ca
import re
import urllib
from curricularanalytics import DegreePlan

def urlize(dp:DegreePlan, college: str, major:str, year:int, optimized: bool, ruleset: str=None):
    c = ca.write_csv(dp) # if you don't say where it writes to string
    d = re.sub('"([a-z, A-Z,0-9]+[\/,0-9,A-Z, ]+)"', r'\1', c.getvalue())
    shard = urllib.parse.quote(re.sub('"(([0-9]+;?)*)"', r'\1', d), safe='()/')
    # new content in the url includes year, major code, title
    title = f"&title={major}+({college},+{year}):+{(dp.curriculum.name).replace(' ', '+')}+{'Optimized' if optimized else 'Unoptimized'}+{ruleset.replace(' ','+') if ruleset is not None else ""}"
    year = f"&year={year}"
    major = f"&major={major}"
    #title = f"&title={major}+({college},+{2024}):+{(dp.curriculum.name).replace(' ', '+')}"
    #&year=2024&major=PB31&title=PB31+(Revelle,+2024):+Public+Health+with+Concentration+in+Medicine+Sciences
    dp_url = "https://educationalinnovation.ucsd.edu/_files/graph-demo.html?defaults=ucsd" + year + major + title + "#" + shard
    return dp_url

curr = ca.read_csv('./cs26_max_nodsc')
curr = curr.curriculum
term_count = 12
min_cpt = 12
max_cpt = 18
obj_order = ['Prereq']#,'Balance']
fixed_courses = {'26':7, '27':7, '28':7, '43':7, '29':8, '30':8, '31':8, '44':8, '32':9, '33':9, '34':9, '45':9, '35':10, '36':10, '25': 10, '37':11, '38':11, '46':11}#'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}# This has a very easy solve the other don't for some reason {'32': 5, '33': 7, '34': 9, '35': 10, '36': 11} ##{'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}
term_range = {'37': (5,11), '38': (5,11), '39': (5,11), '40': (5,11), '41': (5,11)} #Dict(Int, (Int, Int))` : specify courses that should appear in a particular range of terms in `(course_id, (low_range, high_range))` format.

opt = chat_optimize.optimize_plan(curr, term_count, min_cpt, max_cpt, obj_order, "", {}, fixed_courses, {}, {}, [])
ca.write_csv(opt, 'opt.csv')

print(urlize(opt, "CS26" , "CS26", 2025, True))