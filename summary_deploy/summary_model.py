from transformers import BartForConditionalGeneration, PreTrainedTokenizerFast
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
import time
import json

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = PreTrainedTokenizerFast.from_pretrained("papari1123/summary_bart_dual_R3F_aihub")

def load_model():
    bart_model = BartForConditionalGeneration.from_pretrained("papari1123/summary_bart_dual_R3F_aihub")
    bart_model.to(device)
    bart_model.eval()
    
    return bart_model

bart_model = load_model()

def generate(text, beam_search_num=10):
    
    input_ids = [tokenizer.bos_token_id] + tokenizer.encode(text) + [tokenizer.eos_token_id]
    input_ids = torch.tensor([input_ids]).to(device)
    
    outputs = bart_model.generate(
        input_ids,
        num_beams=beam_search_num,
        num_return_sequences=beam_search_num,
        max_length=512,
        no_repeat_ngram_size=2,
        repetition_penalty=2.0,
        length_penalty=0.5,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
        bos_token_id=tokenizer.bos_token_id,
        bad_words_ids=[[tokenizer.unk_token_id]]).detach().cpu()
    
    answers = tokenizer.batch_decode(outputs.tolist())
    answers = list(map(lambda x:x.replace("</s>","").replace("<pad>","").replace("<usr>","").strip(), answers))
    return answers[0]

class ServerHandler(BaseHTTPRequestHandler):
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        message = json.loads(self.rfile.read(length))

        
        input_text = message['text']
        start_time = time.time()
        infer_text = generate(input_text)
        infer_time = time.time() - start_time
        
        message['answer'] = infer_text
        message['took'] = str(infer_time) + "sec"
        
        self._set_headers()
        self.wfile.write(json.dumps(message).encode())
        
    
def run(server_class=HTTPServer, handler_class=ServerHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting inference module on port %d...' % port)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
