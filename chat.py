import random
import json
import torch

from model import NeuralNet
from nltk_utils import bag_of_words, tokenize

# Load intents
with open('intents.json', 'r') as json_data:
    intents = json.load(json_data)

# Load data
FILE = "data.pth"
data = torch.load(FILE)

input_size = data["input_size"]
hidden_size = data["hidden_size"]
output_size = data["output_size"]
all_words = data["all_words"]
tags = data["tags"]
model_state = data["model_state"]

# Load model
model = NeuralNet(input_size, hidden_size, output_size)
model.load_state_dict(model_state)
model.eval()

bot_name = "ChatBot"
print(f"{bot_name}: Hello! Type 'quit' to exit.")

while True:
    sentence = input("You: ")
    if sentence.lower() == "quit":
        print(f"{bot_name}: Goodbye!")
        break

    sentence = tokenize(sentence)
    X = bag_of_words(sentence, all_words)
    X = torch.from_numpy(X).float().unsqueeze(0)

    output = model(X)
    _, predicted = torch.max(output, dim=1)
    tag = tags[predicted.item()]

    probs = torch.softmax(output, dim=1)
    prob = probs[0][predicted.item()]

    if prob.item() > 0.75:
        for intent in intents['intents']:
            if tag == intent["tag"]:
                print(f"{bot_name}: {random.choice(intent['responses'])}")
    else:
        print(f"{bot_name}: I'm not sure I understand. Try again.")

