# given a degree plan c and ca
import curricularanalytics as ca
import re
import urllib

changes = {
    "defaults": "ca",
    "edits": [
        {
            "CourseName": "DSC 140A",
            "add_rem": 0,
            "lost_prereqs": [12],
            "gained_prereqs": [5]
        },
        {
            "CourseName": "DEI",
            "add_rem": -1,
            "lost_prereqs": [],
            "gained_prereqs": []
        },
        {
            "CourseName": "DSC 40A",
            "add_rem": -1,
            "lost_prereqs": [],
            "gained_prereqs": []
        },
        {
            "CourseName": "LMAO 50",
            "add_rem": 1,
            "lost_prereqs": [],
            "gained_prereqs": [2,5,6,7]
        }
    ]
}

c = ca.read_csv("./zombieplan.csv")
b = ca.write_csv(c, "./hah.csv", iostream=True) # write to string object
d = re.sub('"([a-z, A-Z,0-9]+[\/,0-9,A-Z, ]+)"', r'\1', b.getvalue())
#shard = urllib.parse.quote(re.sub('"([0-9]+;?[0-9]*)+"', r'\1', d), safe='()/')
shard = urllib.parse.quote(re.sub('"(([0-9]+;?)*)"', r'\1', d), safe='()/')

query = urllib.parse.urlencode(changes)
query = query.replace('%27', '%22')

print(query + '#' + shard)