import torch
import torch.nn as nn
import torch.nn.functional as F

class HardELU(nn.Module):
    def __init__(self, inplace=True):
        super(HardELU, self).__init__()
        self.a = nn.Parameter(torch.zeros(1))
    
    def forward(self, input):
        return F.relu(input+self.a)-self.a