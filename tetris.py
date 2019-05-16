####################################################################################################
### Imports
import numpy as np
import time
# import pygame
import random
import threading
import sys,tty,termios
import pynput
from math import floor

####################################################################################################
### Defines
# List of color
T = 1 ; S = 2 ; Z = 3 ; J = 4 ; L = 5 ; I = 6 ; O = 7
# List of allowed movements
down = (1,0) ; left = (0,-1) ; right = (0,1) ; rot = (-1,0)
moves = [down, left, right, rot]
# List of tetraminos
tetra_list = [  [], # element zero for convenience; so that tetraminos(J) outputs a J
                [[1, 1, 1],
                 [0, 1, 0]],
            	[[0, 2, 2],
            	 [2, 2, 0]],
            	[[3, 3, 0],
            	 [0, 3, 3]],
            	[[4, 0, 0],
            	 [4, 4, 4]],
            	[[0, 0, 5],
            	 [5, 5, 5]],
            	[[6, 6, 6, 6]],
            	[[7, 7],
            	 [7, 7]]]


####################################################################################################
### Generators
def shape_from_color(color, rot = 0):
    assert 1 <= color <= 7
    return np.rot90(tetra_list[color], rot)

def gen_random_start(cols, offset = 1): return (0,random.randint(offset, cols-offset-1))
def gen_random_color(): return random.randint(1,7)
def gen_random_rot(): return random.randint(0,3)
def gen_random_shape(): return shape_from_color(gen_random_color(), gen_random_rot())


####################################################################################################
### Tetraminos
class Tetra:
    """ This class represent one instance of tetraminos
    It defines the functions to move it (i.e. modify anchor as desired) and
    functions to compute the state of the tetramino (color, list of occupied cells..)
    Attributes :
        shape   - shape as defined in tetra_list
        anchor  - position of topleft cell of the shape
    """
    ## Init
    def __init__(self, shape = None, anchor = (0,0)):
        if shape is None: shape = gen_random_shape()
        self.shape = shape
        self.anchor = anchor

    ## Properties
    @property
    def anchor(self): return self._anchor
    @anchor.setter
    def anchor(self,v): self._anchor = v
    @property
    def shape(self): return self._shape
    @shape.setter
    def shape(self,v): self._shape = v


    ## Movement functions
    def move(self, m):
        if m == rot:
            self.shape = np.rot90(self.shape,-1)
        else:
            self.anchor = (self.anchor[0]+m[0], self.anchor[1]+m[1])

    ## Status computation
    def get_full_pose(self):
        pose = []
        for (i,j),cell in np.ndenumerate(self.shape):
            if cell != 0:
                pose.append((self.anchor[0]+i, self.anchor[1]+j))
        return pose
    def get_color(self): return np.amax(self.shape)

    ## To string
    def __str__(self):
        # return str(self.shape)+'  @ '+str(self.anchor)
        return str(self.shape)


####################################################################################################
### Board
class Board:
    """ This class represent the tetris board
    It has a fixed size grid, an active tetramino, and a preview of the upcoming
    shape
    Attributes :
        rows        - number of rows in grid
        cols        - number of cols in grid
        grid        - a numpy matrix of cells
        tetra       - the current active tetramino
        next_shape  - the shape of next tetramino to spawn
    """
    # List of cell format status
    empty_cell = ' '
    used_cell = '\u25A0'
    locked_cell = '\u25A0'

    ## Init
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.grid = np.full((rows,cols), self.empty_cell, dtype=np.unicode_)
        self.tetra = Tetra()
        self.next_shape = gen_random_shape()
        self._draw_tetra()

    ## Properties
    @property
    def rows(self): return self._rows
    @rows.setter
    def rows(self,v): self._rows = v
    @property
    def cols(self): return self._cols
    @cols.setter
    def cols(self,v): self._cols = v
    @property
    def grid(self): return self._grid
    @grid.setter
    def grid(self,v): self._grid = v

    ## Cell management
    def is_empty(self,i,j):
        return self.grid[i,j] == self.empty_cell

    ## Lines management
    def remove_line(self, i_list):
        for i in reversed(sorted(i_list)):
            self.grid = np.delete(self.grid, i, axis=0)
    def fill_grid(self):
        if self.grid.shape[0] < self.rows:
            self.grid = np.concatenate((np.full((self.rows-self.grid.shape[0],self.cols), self.empty_cell, dtype=np.unicode_),self.grid), axis=0)

    ## Draw or undraw tetramino
    def _draw_tetra(self):
        pose = self.tetra.get_full_pose()
        # for cell in pose: self.grid[cell] = self.tetra.get_color()
        for cell in pose: self.grid[cell] = self.used_cell
    def _lock_tetra(self):
        pose = self.tetra.get_full_pose()
        # for cell in pose: self.grid[cell] = self.tetra.get_color()
        for cell in pose: self.grid[cell] = self.locked_cell
    def _undraw_tetra(self):
        pose = self.tetra.get_full_pose()
        for cell in pose: self.grid[cell] = self.empty_cell

    ## Collision checks
    # in order to make the translation for rotation, output the colliding
    # cells (or just an indication of where is the collision and how much
    # to shift). Then make translation accordingly and change and check again.
    def _check_coll(self, tetra):
        pose = tetra.get_full_pose()
        if self.tetra is not None: curr_pose = self.tetra.get_full_pose()
        else: curr_pose = []
        coll = []
        for cell in pose:
            # print(cell) #DEBUG
            if cell[1] < 0 or cell[1] > self.cols-1 or cell[0] > self.rows-1:
                coll.append(cell) ; continue
            if cell not in curr_pose and self.grid[cell] != self.empty_cell:
                coll.append(cell) ; continue
        # print(coll) #DEBUG
        return coll

    ## Tetramino management
    def _spawn_tetra(self):
        offset = 1
        tries = 20
        success = False
        for i in range(tries):
            spawn = gen_random_start(self.cols, offset)
            tetra = Tetra(self.next_shape,spawn)
            if self._check_coll(tetra) == []: success = True ; break
        if success:
            self.tetra = tetra
            self.next_shape = gen_random_shape()

    def _remove_tetra(self):
        self.tetra = None
        i_list = []
        for i,row in enumerate(self.grid):
            full = True
            for cell in row:
                if cell == self.empty_cell:
                    full = False
                    break
            if full: i_list.append(i)
        self.remove_line(i_list)
        self.fill_grid()

    ## Tetramino updates
    # Scoring is updated when removing lines, very easy to implement
    # Check online how score is computed in other games ?
    def update(self, m):
        assert m == left or m == right or m == down or m == rot
        next_tetra = Tetra(self.tetra.shape, self.tetra.anchor)
        next_tetra.move(m)
        collisions = self._check_coll(next_tetra)
        if collisions == []:
            self._undraw_tetra()
            self.tetra.move(m)
            self._draw_tetra()
        elif m == down:
            self._lock_tetra()
            self._remove_tetra()
            self._spawn_tetra()
            if self.tetra is None : return True
            else: self._draw_tetra()

    ## To string
    def __str__(self):
        return ('\n\n\n\n' +
                'Next tetra :\n' +
                str(np.matrix(self.next_shape)) + '\n' +
                '\n' +
                str(self.grid))

####################################################################################################
### Game_session
class Game_session:
    """ This class represent a session of a tetris game.
    It contains the game board, status, and parameters.
    It includes the game management (loop, display) functions.
    It also includes the keyb Key.upoard control.
    Attributes :
        board       - game board
        over        - bool indicating when game is lost
        speed       - falling speed
        input       - last keyboard input
    """
    ## Init
    def __init__(self, rows, cols):
        self.board = Board(rows, cols)
        self.over = False
        self.speed = 0.5
        self.input = None

    ## Properties
    @property
    def board(self): return self._board
    @board.setter
    def board(self,v): self._board = v
    @property
    def over(self): return self._over
    @over.setter
    def over(self,v): self._over = v

    ### Display
    def display(self):
        print(self.board)

    ### Falling loop for threading
    def fall_loop(self):
        last_update = time.time()
        while (1):
            if time.time()-last_update > self.speed:
                self.over = self.board.update(down)
                last_update = time.time()
            if self.over: break

    ### Update from input
    def update(self,input):
        self.board.update(input)

    ### Keyboard control
    def on_press(self,key):
        if key == pynput.keyboard.Key.up:
            self.board.update(rot)
        if key == pynput.keyboard.Key.left:
            self.board.update(left)
        if key == pynput.keyboard.Key.down:
            self.board.update(down)
        if key == pynput.keyboard.Key.right:
            self.board.update(right)
        if key == pynput.keyboard.Key.space:
            self.over = True

    def print_game_over(self):
        c_row = floor(self.board.rows/2)
        c_col = floor(self.board.cols/2)
        self.board.grid[c_row,c_col-4] = 'G'
        self.board.grid[c_row,c_col-3] = 'A'
        self.board.grid[c_row,c_col-2] = 'M'
        self.board.grid[c_row,c_col-1] = 'E'
        self.board.grid[c_row,c_col-0] = ' '
        self.board.grid[c_row,c_col+1] = 'O'
        self.board.grid[c_row,c_col+2] = 'V'
        self.board.grid[c_row,c_col+3] = 'E'
        self.board.grid[c_row,c_col+4] = 'R'
        self.display()

####################################################################################################
### Main
rows = 20
cols = 11

game = Game_session(rows,cols)

thread_fall = threading.Thread(target = game.fall_loop, daemon=True)
thread_fall.start()

listener = pynput.keyboard.Listener(on_press=game.on_press,on_release=None)
listener.start()

while not game.over:
    game.display()

    time.sleep(0.05)  #framerate
listener.stop()
thread_fall.join()
game.print_game_over()
print('byebye')
