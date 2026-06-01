```mermaid
%%{init: {
  "flowchart": {
    "nodeSpacing": 8,
    "rankSpacing": 10,
    "curve": "linear"
  }
}}%%

flowchart TB

%% ───────── ROW 1 ─────────
subgraph R1[" "]
direction LR

subgraph IN["INPUTS"]
direction TB
V0["🎬 Vision\nMOSEI"]:::vis
A0["🎙️ Audio\nwaveform"]:::aud
T0["📝 Text\nMOSEI"]:::txt
end

subgraph FEAT["FEATURES"]
direction TB
V1["OpenFace\n60×35"]:::vis
A1["COVAREP\n60×74"]:::aud
T1["BERT tok\n50"]:::txt
end

end

V0 --> V1
A0 --> A1
T0 --> T1


%% ───────── ROW 2 ─────────
subgraph R2[" "]
direction LR

subgraph PROJ["PROJ"]
direction TB
V2["Conv1D\n60×128"]:::vis
A2["Conv1D\n60×128"]:::aud
T2["BERT\n768→128"]:::txt
end

subgraph BN["Bottleneck\nn=4"]:::bn
direction TB
BT["tokens"]:::bn

V3["SelfAttn V"]:::vis
A3["SelfAttn A"]:::aud
T3["SelfAttn T"]:::txt

V3b["FFN"]:::vis
A3b["FFN"]:::aud
T3b["FFN"]:::txt

BT -.-> V3
BT -.-> A3
BT -.-> T3

V3 --> V3b
A3 --> A3b
T3 --> T3b
end

end

V1 --> V2 --> BN
A1 --> A2 --> BN
T1 --> T2 --> BN


%% ───────── ROW 3 ─────────
subgraph R3[" "]
direction LR

subgraph AGG["POOL"]
direction TB
V4["Mean"]:::vis
A4["Mean"]:::aud
T4["CLS"]:::txt
end

CAT["Concat 384"]:::fuse
CLS["MLP\n→6"]:::cls
OUT["Sigmoid"]:::out

end

V3b --> V4 --> CAT
A3b --> A4 --> CAT
T3b --> T4 --> CAT

CAT --> CLS --> OUT


%% ───────── STYLE (compact) ─────────
classDef vis fill:#bbdefb,stroke:#1565c0,color:#0d47a1
classDef aud fill:#ffe0b2,stroke:#fb8c00,color:#bf360c
classDef txt fill:#c8e6c9,stroke:#43a047,color:#1b5e20
classDef bn  fill:#f8bbd0,stroke:#e91e63,color:#880e4f
classDef fuse fill:#ce93d8,stroke:#7b1fa2,color:#4a148c
classDef cls fill:#7b1fa2,stroke:#4a148c,color:#fff
classDef out fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
```