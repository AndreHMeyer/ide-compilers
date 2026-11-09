.data
v0 : 0
v1 : 0

.text
    LDI 10
    STO v0
    LDI 20
    STO v1
    LD v1
    STO $out_port
    LD v0
    STO $out_port
    HLT
