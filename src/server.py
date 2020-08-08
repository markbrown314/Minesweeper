""" Minesweeper WebSocket Server """
import re
from copy import deepcopy
import json
import asyncio
import websockets
from minesweeper import GameContext
from time import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

def parse_tuple(input_str):
    """ parse coordinate string input """
    tuple_temp = input_str
    tuple_temp = tuple_temp.replace("(", "")
    tuple_temp = tuple_temp.replace(")", "")
    tuple_temp = tuple_temp.split(",")
    if len(tuple_temp) < 1:
        raise ValueError("invalid tuple")

    return tuple([int(value) for value in tuple_temp])


def jsonify_game_context(game_context):
    """ convert game context to a JSON compatible data structure """
    gc_dict = {}
    game_map_int = {}
    gc_dict["max_x"] = game_context.max_x
    gc_dict["max_y"] = game_context.max_y
    # cannot use map tuple keys in JSON
    # convert tuple key to integer based key
    for (x, y) in game_context.game_map:
        game_map_int[game_context.max_x * x + y] = game_context.game_map[(x, y)]

    gc_dict["game_map"] = game_map_int
    gc_dict["winning_condition"] = game_context.winning_condition()
    gc_dict["loosing_condition"] = game_context.loosing_condition()

    gc_dict["mines"] = game_context.max_mines


    gc_dict["flags"] = len(game_context.flags)
    
    return json.dumps(gc_dict)

async def event_loop(websocket, path):
    """ event loop """

    print("websocket path:", path)
    game_context = GameContext()
    undo_list = []
    game_over = False

    while True:
        save_context = deepcopy(game_context)

        if not game_over:
            game_context.render_gameboard()

        game_context_json = jsonify_game_context(game_context)

        t1 = time()
        print("Send...")
        await websocket.send(game_context_json)
        t2 = time()
        print("delta time:", t2 - t1)

        print("Wait...")
        recv = await websocket.recv()
        print("Recv...", recv)
        await asyncio.sleep(.25)

        command = recv

        if command == "":
            continue

        if command[0] == "!" and not game_over:
            try:
                coord_str = re.split(' |,', command, 1)[1]
                coord = parse_tuple(coord_str)
            except ValueError:
                print("invalid input")
                continue
            if not (coord in game_context.visible):
                undo_list.append(save_context)
                game_context.uncover_tile(coord)

            print("delta time:", t2 - t1)

            if game_context.hit_mine(coord):
                print("Game Over!")
                game_over = True
                game_context.visible.add(coord)
                game_context.render_gameboard()
                continue

            # check winning condition
            if game_context.winning_condition():
                game_context.reveal = True
                game_context.render_gameboard()
                game_over = True
                print("You Win!!!")
                continue

        if command[0] == "?" and not game_over:
            try:
                coord_str = re.split(' |,', command, 1)[1]
                coord = {parse_tuple(coord_str)}
                undo_list.append(save_context)
                game_context.set_flag(coord)
            except ValueError:
                print("invalid input")

        if command[0] == "%":
            print(game_context.mines)
            undo_list.append(save_context)
            game_context.reveal = not game_context.reveal

        if command[0] == "s":
            print("Restarting Game")
            undo_list = []
            game_context = GameContext()
            try:
                tuple_str = re.split(' |,', command, 1)[1]
                restart_tuple = parse_tuple(tuple_str)
            except ValueError:
                print("invalid input")
                continue
            game_context.max_x = restart_tuple[0]
            game_context.max_y = restart_tuple[1]
            game_context.max_mines = restart_tuple[2]
            game_over = False

        if command[0] == "u":
            if undo_list:
                game_over = False
                game_context = undo_list.pop()
            else:
                print("Cannot undo")
# main

def webserver():
    os.chdir("public/")
    print("Setting up Webserver...")
    http_server = HTTPServer(('', 8000), SimpleHTTPRequestHandler)
    http_server.serve_forever()

if __name__ == '__main__':
    # launch webserver
    threading.Thread(target=webserver, daemon=True).start()
    print("Waiting for client connection...")
    server = websockets.serve(event_loop, 'localhost', 8081)
    asyncio.get_event_loop().run_until_complete(server)
    asyncio.get_event_loop().run_forever()