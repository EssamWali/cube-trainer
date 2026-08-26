import random
import kociemba

def create_solved_cube():
    return ['U', 'U', 'U', 'U', 'U', 'U', 'U', 'U', 'U', 
            'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R',
            'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F',
            'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D',
            'L', 'L', 'L', 'L', 'L', 'L', 'L', 'L', 'L',
            'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B']

def print_cube(cube):
    print("       {} {} {}".format(cube[0], cube[1], cube[2]))
    print("       {} {} {}".format(cube[3], cube[4], cube[5]))
    print("       {} {} {}".format(cube[6], cube[7], cube[8]))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(cube[36], cube[37], cube[38], cube[18], cube[19], cube[20],cube[9], cube[10], cube[11], cube[45], cube[46], cube[47]))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(cube[39], cube[40], cube[41], cube[21], cube[22], cube[23],cube[12], cube[13], cube[14], cube[48], cube[49], cube[50]))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(cube[42], cube[43], cube[44], cube[24], cube[25], cube[26],cube[15], cube[16], cube[17], cube[51], cube[52], cube[53]))
    print("       {} {} {}".format(cube[27], cube[28], cube[29]))
    print("       {} {} {}".format(cube[30], cube[31], cube[32]))
    print("       {} {} {}".format(cube[33], cube[34], cube[35]))     

def print_cube_indices(cube):
    print("       {} {} {}".format(0, 1, 2))
    print("       {} {} {}".format(3, 4, 5))
    print("       {} {} {}".format(6, 7, 8))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(36, 37, 38, 18, 19, 20, 9, 10, 11, 45, 46, 47))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(39, 40, 41, 21, 22, 23, 12, 13, 14, 48, 49, 50))
    print("{} {} {}  {} {} {}  {} {} {}  {} {} {}".format(42, 43, 44, 24, 25, 26, 15, 16, 17, 51, 52, 53))
    print("       {} {} {}".format(27, 28, 29))
    print("       {} {} {}".format(30, 31, 32))
    print("       {} {} {}".format(33, 34, 35))  

def R_rotate(cube):
    # R face clockwise rotation
    cube[9], cube[10], cube[11], cube[12], cube[13], cube[14], cube[15], cube[16], cube[17] = cube[15], cube[12], cube[9], cube[16], cube[13], cube[10], cube[17], cube[14], cube[11]
    # Adjust the adjacent faces
    cube[2], cube[5], cube[8], cube[20], cube[23], cube[26], cube[29], cube[32], cube[35], cube[45], cube[48], cube[51] = cube[20], cube[23], cube[26], cube[29], cube[32], cube[35], cube[51], cube[48], cube[45], cube[8], cube[5], cube[2]

def U_rotate(cube):
    # U face clockwise rotation
    cube[0], cube[1], cube[2], cube[3], cube[4], cube[5], cube[6], cube[7], cube[8] = cube[6], cube[3], cube[0], cube[7], cube[4], cube[1], cube[8], cube[5], cube[2]
    # Adjust the adjacent faces
    cube[9], cube[10], cube[11], cube[18], cube[19], cube[20], cube[36], cube[37], cube[38], cube[45], cube[46], cube[47] = cube[45], cube[46], cube[47], cube[9], cube[10], cube[11], cube[18], cube[19], cube[20], cube[36], cube[37], cube[38]

def L_rotate(cube):
    # L face clockwise rotation
    cube[36], cube[37], cube[38], cube[39], cube[40], cube[41], cube[42], cube[43], cube[44] = cube[42], cube[39], cube[36], cube[43], cube[40], cube[37], cube[44], cube[41], cube[38]
    # Adjust the adjacent faces
    cube[0], cube[3], cube[6], cube[18], cube[21], cube[24], cube[27], cube[30], cube[33], cube[47], cube[50], cube[53] = cube[53], cube[50], cube[47], cube[0], cube[3], cube[6], cube[18], cube[21], cube[24], cube[33], cube[30], cube[27]

def F_rotate(cube):
    # F face clockwise rotation
    cube[18], cube[19], cube[20], cube[21], cube[22], cube[23], cube[24], cube[25], cube[26] = cube[24], cube[21], cube[18], cube[25], cube[22], cube[19], cube[26], cube[23], cube[20]
    # Adjust the adjacent faces
    cube[6], cube[7], cube[8], cube[9], cube[12], cube[15], cube[27], cube[28], cube[29], cube[38], cube[41], cube[44] = cube[44], cube[41], cube[38], cube[6], cube[7], cube[8], cube[15], cube[12], cube[9], cube[27], cube[28], cube[29]

def D_rotate(cube):
    # D face clockwise rotation
    cube[27], cube[28], cube[29], cube[30], cube[31], cube[32], cube[33], cube[34], cube[35] = cube[33], cube[30], cube[27], cube[34], cube[31], cube[28], cube[35], cube[32], cube[29]
    # Adjust the adjacent faces
    cube[15], cube[16], cube[17], cube[24], cube[25], cube[26], cube[42], cube[43], cube[44], cube[51], cube[52], cube[53] = cube[24], cube[25], cube[26], cube[42], cube[43], cube[44], cube[51], cube[52], cube[53], cube[15], cube[16], cube[17]

def B_rotate(cube):
    # B face clockwise rotation
    cube[45], cube[46], cube[47], cube[48], cube[49], cube[50], cube[51], cube[52], cube[53] = cube[51], cube[48], cube[45], cube[52], cube[49], cube[46], cube[53], cube[50], cube[47]
    # Adjust the adjacent faces
    cube[0], cube[1], cube[2], cube[11], cube[14], cube[17], cube[33], cube[34], cube[35], cube[36], cube[39], cube[42] = cube[11], cube[14], cube[17], cube[35], cube[34], cube[33], cube[36], cube[39], cube[42], cube[2], cube[1], cube[0]

def clockwise_rotation(cube, face):
    if face == 'R':
        R_rotate(cube)
    elif face == 'U':
        U_rotate(cube)
    elif face == 'L':
        L_rotate(cube)
    elif face == 'F':
        F_rotate(cube)
    elif face == 'D':
        D_rotate(cube)
    elif face == 'B':
        B_rotate(cube)

def anti_clockwise_rotation(cube, face):
    if face == 'R':
        R_rotate(cube)
        R_rotate(cube)
        R_rotate(cube)
    elif face == 'U':
        U_rotate(cube)
        U_rotate(cube)
        U_rotate(cube)
    elif face == 'L':
        L_rotate(cube)
        L_rotate(cube)
        L_rotate(cube)
    elif face == 'F':
        F_rotate(cube)
        F_rotate(cube)
        F_rotate(cube)
    elif face == 'D':
        D_rotate(cube)
        D_rotate(cube)
        D_rotate(cube)
    elif face == 'B':
        B_rotate(cube)
        B_rotate(cube)
        B_rotate(cube)

def moves(cube, move_sequence):
    for move in move_sequence:
        if move.endswith("'"):
            anti_clockwise_rotation(cube, move[0])
        elif move.endswith("2"):
            clockwise_rotation(cube, move[0])
            clockwise_rotation(cube, move[0])
        else:
            clockwise_rotation(cube, move)

def scramble_generator():
    faces = ['R', 'U', 'L', 'F', 'D', 'B']
    modifiers = ['', "'", '2']
    scramble = []
    length = random.randint(20, 25)  
    last_face = None
    for _ in range(length):
        valid_faces = [f for f in faces if f != last_face]
        face = random.choice(valid_faces)
        last_face = face
        modifier = random.choice(modifiers)
        scramble.append(face + modifier)
    return scramble

def solution_scorer(solution):
    move_axis = {'R': 'x', 'L': 'x', 'U': 'y', 'D': 'y', 'F': 'z', 'B': 'z'}
    score = 0 
    prev_move = None
    for x in solution:
        if prev_move and move_axis[x[0]] != move_axis[prev_move[0]]:
            score -= 0.3
        score += 1
        prev_move = x
    return score

cube = create_solved_cube()
# print_cube(cube)
# print_cube_indices(cube)
scramble = scramble_generator()
moves(cube, scramble)
kociemba_solution = kociemba.solve(''.join(cube))
print(kociemba_solution)
print(solution_scorer(["R", "U", "R'", "U'"]))