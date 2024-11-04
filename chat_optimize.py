import gurobipy as gp
from gurobipy import GRB
import numpy as np
from typing import List, Dict, Tuple, Any
from curricularanalytics import Course, Curriculum, Term, DegreePlan, Requisite

# Helper fn using Course id to find the vertex id of a course in a curriculum.
def get_vertex(course_id: int, curric: Curriculum) -> int:
    for course in curric.courses:
        if course.id == int(course_id):
            return course.vertex_id[curric.id]
    return 0

# Objective function for creating a degree plan with a minimal number of terms
def term_count_obj(model: gp.Model, mask: np.ndarray, x: gp.MVar, c_count: int, multi: bool = True) -> Any:
    terms = [gp.quicksum(x[k, :] * mask) for k in range(c_count)]
    if multi:
        obj = model.addVar(lb=0, name='objective')
        model.setObjective(obj, GRB.MINIMIZE)
        model.addConstr(obj == gp.quicksum(terms))
        return obj
    else:
        model.setObjective(gp.quicksum(terms), GRB.MINIMIZE)
        return True
    
# Objective fn for evenly balancing credit hours across the degree plan
def balance_obj(model: gp.Model, max_cpt: int, term_count: int, x: gp.MVar, y: gp.MVar, credit: np.ndarray, multi: bool = True) -> Any:
    total_credit_term = [gp.quicksum(credit[i] * x[i, j] for i in range(len(credit))) for j in range(term_count)]
    for i in range(term_count):
        for j in range(term_count):
            model.addConstr(y[i, j] >= total_credit_term[i] - total_credit_term[j])
            model.addConstr(y[i, j] >= -(total_credit_term[i] - total_credit_term[j]))
    if multi:
        obj = model.addVar(lb=0, name='objective')
        model.setObjective(obj, GRB.MINIMIZE)
        model.addConstr(obj == gp.quicksum(y[i, j] for i in range(term_count) for j in range(term_count)))
        return obj
    else:
        model.setObjective(gp.quicksum(y[i, j] for i in range(term_count) for j in range(term_count)), GRB.MINIMIZE)
        return True
    
# Objective fn for minimizing toxic course combos in a degree plan
def toxicity_obj(model: gp.Model, c_count: int, courses: List[Course], term_count: int, x: gp.MVar, ts: List[float], curric_id: int, multi: bool = True, toxicity_file: str = "", toxicity_dict: Dict[Tuple[Course, Course], float] = {}) -> Any:
    toxicity = {}
    if toxicity_file:
        with open(toxicity_file, 'r') as f:
            for line in f:
                row = line.strip().split(",")
                toxicity[(row[0].strip(), row[1].strip())] = float(row[2]) + 1
    elif toxicity_dict:
        for course_pair in toxicity_dict.keys():
            toxicity[(course_pair[0].prefix + course_pair[0].num, course_pair[1].prefix + course_pair[1].num)] = toxicity_dict[course_pair]

    toxicity_matrix = np.zeros((c_count, c_count))
    for c1 in courses:
        for c2 in courses:
            if c1 != c2:
                key = (c1.prefix + c1.num, c2.prefix + c2.num)
                if key in toxicity:
                    toxicity_matrix[c1.vertex_id[curric_id], c2.vertex_id[curric_id]] = toxicity[key]
    
    for j in range(term_count):
        ts.append(gp.quicksum((toxicity_matrix * x[:, j].reshape(-1, 1)) * x[:, j]))
    
    if multi:
        obj = model.addVar(lb=0, name='objective')
        model.setObjective(obj, GRB.MINIMIZE)
        model.addConstr(obj == gp.quicksum(ts))
        return obj
    else:
        model.setObjective(gp.quicksum(ts), GRB.MINIMIZE)
        return True

# The one that I care most about
# Objective function for minimizing the number of terms between pre- and post-requisites in a degree plan (i.e. keep prereqs
# as close as possible to the follow-up courses)
def req_distance_obj(model: gp.Model, mask: np.ndarray, x: gp.MVar, graph: Any, distance: List[float], multi: bool = True) -> Any:
    for edge in graph.edges:
        # Tj - Ti where Ti = sum(j=1 to term_count)(j*xij), i.e. what term course is in in one-hot dot term numbers i.e. what term the course is in
        distance.append(gp.quicksum(x[edge[1], i] * mask[i] for i in range(mask.size)) -  gp.quicksum(x[edge[0], i] * mask[i] for i in range(mask.size)))#np.dot([x[edge[1], i] for i in range(mask.size)], mask)) - gp.quicksum( np.dot([x[edge[0],i] for i in range(mask.size)], mask)))   #x[edge[0], :] * mask))
    if multi:
        obj = model.addVar(lb=0, name='objective')
        model.setObjective(gp.quicksum(distance), GRB.MINIMIZE)
        #model.addConstr(obj == gp.quicksum(distance))
        return obj
    else:
        model.setObjective(gp.quicksum(distance), GRB.MINIMIZE)
        return True

# cribbed from Julia verbatim
"""
    optimize_plan(c::Curriculum, term_count::Int, min_cpt::Int, max_cpt::Int, 
      obj_order::Array{String, 1}; toxic_score_file::String = "", diff_max_cpt::Array{UInt, 1}, 
      fix_courses::Dict, consec_courses::Dict, term_range::Dict, prior_courses::Array{Term, 1})

Using the curriculum `c` supplied as input, returns a degree plan optimzed according to the various 
optimization criteria that have been specified as well as the objective functions that have been selected.

If an optimzied plan cannot be constructed (i.e., the constraints are such that an optimal solution is infeasible),
`nothing` is returned, and the solver returns a message indicating that the problems is infeasible.  In these cases,
you may wish to experiment with the constraint values.

# Arguments
- `curric::Curriculum` : the curriculum the degree plan will be created from.
- `term_count::Int` : the maximum number of terms in the degree plan.
- `min_cpt::Int` : the minimum number of credits allowed in each term.
- `max_cpt::Int`: the minimum number of credits allowed in each term.
- `obj_order::Array{String, 1}` : the order in which the objective functions shoud be evaluated.  Allowable strings are:
  * `Balance` - the balanced curriculum objective described above.
  * `Prereq` - the requisite distnace objective described above.
  * `Toxicity` - the toxic course avoidance objective described above.
- `toxic_score_file::String`: file path to toxicity scores CSV
- `diff_max_cpt::Array{UInt, 1}` : specify particular terms that may deviate from the `max_cpt` value.
- `fix_courses::Dict(Int, Int)` : specify courses that should be assigned to particular terms in `(course_id, term)` 
    format.
- `consec_courses::Dict(Int, Int)`: specify pairs of courses that should appear in consecutive terms in `(course_id, course_id)` format.
- `term_range::Dict(Int, (Int, Int))` : specify courses that should appear in a particular range of terms in `(course_id, (low_range, high_range))` format.
- `prior_courses::Array{Term, 1}` : specify courses that were already completed in prior terms.

# Example
```julia-repl
julia> curric = read_csv("path/to/curric.csv")
julia> dp = optimize_plan(curric, 8, 6, 18, ["Balance", "Prereq"])
```
"""
def optimize_plan(
    curric: Curriculum,
    term_count: int,
    min_cpt: int,
    max_cpt: int,
    obj_order: List[str],
    toxicity_file: str = "",
    diff_max_cpt: Dict[int, int] = {},
    fix_courses: Dict[str, int] = {},
    consec_courses: Dict[str, str] = {},
    term_range: Dict[str, Tuple[int, int]] = {},
    prior_courses: List[Term] = []
) -> DegreePlan:
    
    # check for multiple objectives
    multi = len(obj_order) > 1

    model = gp.Model()
    #model.setParam('OutputFlag', 0)  # Suppress solver output
    
    # find courses already taken
    taken_course_ids = [course.id for term in prior_courses for course in term.courses]
    
    # get course count and vertex map
    courses = curric.courses
    c_count = len(courses)
    vertex_map = {c.id: c.vertex_id[curric.id] for c in courses}
    credit = np.array([c.credit_hours for c in courses])
    mask = np.arange(term_count)
    

    x = model.addVars(c_count, term_count, vtype=GRB.BINARY, name='x')
    y = model.addVars(term_count, term_count, lb=0, name='y')

    ts = []
    distance = []

    # iterate through courses and create basic requisite constraints
    for c in courses:
        for req in c.requisites:
            if req not in prior_courses:
                if c.requisites[req] == Requisite.pre:
                    # Ti = gp.quicksum(x[edge[1], i] * mask[i] for i in range(mask.size)) need Ta < Tb for a prereq of b
                    model.addConstr(gp.quicksum(x[vertex_map[req], i] * mask[i] for i in range(mask.size)) <= gp.quicksum(x[c.vertex_id[curric.id], i] * mask[i] for i in range(mask.size)) - 1)  #gp.quicksum(x[vertex_map[req], :]) <= (gp.quicksum(x[c.vertex_id[curric.id], :]) - 1))
                elif c.requisites[req]  == Requisite.co:
                    model.addConstr(gp.quicksum(x[vertex_map[req[1]], :]) <= gp.quicksum(x[c.vertex_id[curric.id], :]))
                elif c.requisites[req]  == Requisite.strict_co:
                    model.addConstr(gp.quicksum(x[vertex_map[req[1]], :]) == gp.quicksum(x[c.vertex_id[curric.id], :]))
                else:
                    print("Requisite type error")

    # check that the output contains each course only once
    # i.e. constraint one
    for idx in range(c_count):
        if idx in vertex_map.values():
            model.addConstr(gp.quicksum(x[idx, i] for i in range(term_count)) == 1)
        else:
            model.addConstr(gp.quicksum(x[idx, :]) == 0)

    # each term must have at least min number of credit points. constraint six
    for j in range(term_count):
        model.addConstr(gp.quicksum(credit[i] * x[i, j] for i in range(c_count)) >= min_cpt)

    # each term must have at most max number of credit points. Use diff_max_cpt to specify exceptions
    # constraint seven
    for j in range(term_count):
        if j in diff_max_cpt:
            model.addConstr(gp.quicksum(credit[i] * x[i, j] for i in range(c_count)) <= diff_max_cpt[j])
        else:
            model.addConstr(gp.quicksum(credit[i] * x[i, j] for i in range(c_count)) <= max_cpt)

    # fix courses (i.e. electives) to specific terms
    for courseID in fix_courses.keys():
        if courseID not in prior_courses:
            vID = get_vertex(courseID, curric)
            if vID != 0:
                model.addConstr(x[vID, fix_courses[courseID]] == 1)
            else:
                print(f"Vertex ID cannot be found for course: {courseID}")

    # fix consecutive courses 
    for first, second in consec_courses.items():
        vID_first = get_vertex(first, curric)
        vID_second = get_vertex(second, curric)
        if vID_first != 0 and vID_second != 0:
            # TODO change to match indexing format
            model.addConstr(gp.quicksum(x[vID_second, :]) - gp.quicksum(x[vID_first, :]) <= 1)
            model.addConstr(gp.quicksum(x[vID_second, :]) - gp.quicksum(x[vID_first, :]) >= 1)
        else:
            print(f"Vertex ID cannot be found for course: {first} or {second}")

    # get courses that have a specified range of terms
    for courseID, (lowTerm, highTerm) in term_range.items():
        vID_Course = get_vertex(courseID, curric)
        if vID_Course != 0:
            model.addConstr(gp.quicksum([x[vID_Course, j] for j in range(term_count)]) >= lowTerm)#x[vID_Course, :]) >= lowTerm)
            model.addConstr(gp.quicksum([x[vID_Course, j] for j in range(term_count)]) <= lowTerm)

    # parse objectives
    objectives = []
    for objective in obj_order:
        if objective == "Toxicity":
            objectives.append(toxicity_obj(model, c_count, courses, term_count, x, ts, curric.id, multi, toxicity_file))
        elif objective == "Balance":
            objectives.append(balance_obj(model, max_cpt, term_count, x, y, credit, multi))
        elif objective == "Prereq":
            objectives.append(req_distance_obj(model, mask, x, curric.graph, distance, multi))

    model.Params.TIME_LIMIT = 6*60
    model.optimize()
    status = model.status
    if status == GRB.OPTIMAL or status == GRB.TIME_LIMIT:
        output = model.getAttr('x', x)

        if "Balance" in obj_order:
            print([np.sum([model.getAttr(GRB.Attr.X,x)[course, term] for course in range(c_count)]) for term in range(term_count)])#model.getAttr('y', y)))

        if "Toxicity" in obj_order:
            print(np.sum(ts))

        if "Prereq" in obj_order:
            print(np.sum(distance))

        optimal_terms = prior_courses.copy()

        for j in range(term_count):
            if np.sum([credit[i] * output[i, j] for i in range(c_count)]) > 0:
                term = []
                for course_id, v_id in vertex_map.items():
                    if round(output[v_id, j]) == 1:
                        for c in courses:
                            if c.id == course_id:
                                term.append(c)
                optimal_terms.append(Term(term))

        dp = DegreePlan("", curric, optimal_terms)
        return dp
    else:
        model.computeIIS()
        model.write('iismodel.ilp')
        return None  # An optimal solution was not found.
