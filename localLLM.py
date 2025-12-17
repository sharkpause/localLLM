#!/usr/bin/env python3
from ollama import Client
import chromadb
from chromadb.config import Settings
import numpy as np
import logging

import textwrap

import os
import time
import threading

from pydantic.v1 import NoneIsAllowedError

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

ollama = Client()

client = chromadb.Client(settings=Settings(anonymized_telemetry=False))
try:
    collection = client.get_collection("wiki_rag")
except:
    collection = client.create_collection("wiki_rag")

def embed_text(text: str):
    e = ollama.embed(model="nomic-embed-text:latest", input=text)
    return np.array(e.embeddings[0])

def retrieve_context(query: str, k=5):
    stop_event = threading.Event()
    t = threading.Thread(
        target=thinking_animation,
        args=(
            ['retrieving documents.', 'retrieving documents..', 'retrieving documents...'],
            stop_event,
        )
    )
    t.start()
    
    query_vec = embed_text(query)
    results = collection.query(query_embeddings=[query_vec.tolist()], n_results=k)
    docs = results["documents"][0]

    stop_event.set()
    t.join()

    return "\n".join(docs)

def ask(prompt: str, model_name: str):
    cli_state['conversation'].append({'role': 'user', 'content': prompt})
    full_response = ''

    print('\nAI>', end=' ')
    try:
        for chunk in ollama.chat(
            model=model_name,
            messages=cli_state['conversation'],
            stream=True
        ):
            if 'content' in chunk['message']:
                response = chunk['message']['content']
                full_response += response
                print(response, end="", flush=True)
    except KeyboardInterrupt:
        print('\nGeneration stopped!')

    cli_state['conversation'].append({
        'role': 'assistant',
        'content': full_response
    })


def ask_rag(prompt: str, model_name: str):
    context = retrieve_context(prompt)
    contexted_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"

    ask(contexted_prompt, model_name)

def thinking_animation(frames, stop_event):
    i = 0

    while not stop_event.is_set():
        print(f'\r{frames[i % len(frames)]}', end='', flush=True)
        i += 1
        time.sleep(0.5)
        print('\r' + ' '* 20 + '\r', end='')

cli_state = {
    'model_name': 'gemma3:1b',
    'conversation': []
}

MEMORY_FILE = 'preprompt.txt'

try:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            cli_state['conversation'].append({
                'role': 'system',
                'content': f.read()
            })
except:
    print('Tip: You can write a preprompt in a preprompt.txt file for persistent memory!')

def handle_command(chain, model_name, query=None):
    for command in chain.lower():
        match command:
            case 'q':
                print('Bye bye!')
                exit(0)
            case 'r':
                if query is None or query.strip() == '':
                    print('No query provided for retrieval.')
                else:
                    ask_rag(query, model_name)
            case 'h':
                print('Available commands:')
                print(textwrap.dedent('''
                Commands that need queries can not be chained
                and must be inputted one prompt at a time, otherwise risk
                undefined behavior\n'''))

                print('h: Display this help screen')
                print('q: Exit the CLI')
                print('r: Use RAG to retieve related documents')
                print('m <model name>: Change model used')
            case 'm':
                if query is None or query.strip() == '':
                    print(f'Current model: {cli_state['model_name']}')
                else:
                    cli_state['model_name'] = query.strip()
                    print(f'Model changed to: {cli_state['model_name']}')

COMMAND_PREFIX = '\\'

print(textwrap.dedent(f'''
CLI Local LLM, type "{COMMAND_PREFIX}" following a command to execute a command.
It must be the first character.\n
Example: \\h for help.\n\n
Current model: {cli_state['model_name']}'''))
while True:
    user_input = input("You> ")

    if user_input.startswith(COMMAND_PREFIX):
        chain = user_input[len(COMMAND_PREFIX):]
        parts = chain.split(maxsplit=1)
        commands = parts[0]
        query = parts[1] if len(parts) > 1 else None
        handle_command(commands, cli_state['model_name'], query)
    else:
        ask(user_input, cli_state['model_name'])
        print('\n')
