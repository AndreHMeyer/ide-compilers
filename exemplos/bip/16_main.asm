.data
v0 : 0
v2 : 0

.text
    LDI 5
    STO v0
    LD v0
    STO $out_port
    LDI 10
    STO v2
    LD v2
    STO $out_port
    LDI 0
    HLT
