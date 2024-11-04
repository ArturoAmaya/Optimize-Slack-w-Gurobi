import chat_optimize
import curricularanalytics as ca

curr = ca.read_csv('FI.csv')
curr = curr.curriculum
term_count = 12
min_cpt = 12
max_cpt = 20
obj_order = ['Prereq','Balance']
fixed_courses = {'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}# This has a very easy solve the other don't for some reason {'32': 5, '33': 7, '34': 9, '35': 10, '36': 11} ##{'37': 5, '38': 7, '39': 9, '40': 10, '41': 11}
term_range = {'37': (5,11), '38': (5,11), '39': (5,11), '40': (5,11), '41': (5,11)} #Dict(Int, (Int, Int))` : specify courses that should appear in a particular range of terms in `(course_id, (low_range, high_range))` format.

opt = chat_optimize.optimize_plan(curr, term_count, min_cpt, max_cpt, obj_order, "", {}, fixed_courses, {}, {}, [])
ca.write_csv(opt, 'opt.csv')