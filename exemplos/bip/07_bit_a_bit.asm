.data
v0 : 0
v1 : 0
v2 : 0
t0 : 0
t1 : 0

.text
    LDI 10
    STO v0
    LDI 3
    STO v1
    LD v0
    AND v1
    STO t0
    LD v0
    XOR v1
    STO t1
    LD t0
    OR t1
    STO v2
    LD v2
    STO $out_port
    HLT
