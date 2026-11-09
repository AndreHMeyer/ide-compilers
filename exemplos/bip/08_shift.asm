.data
v0 : 0
v1 : 0
t0 : 0
t1 : 0
c0 : 32767

.text
    LDI 5
    STO v0
    LD v0
    SLL 2
    STO t0
    AND c0
    STO t1
    LD t0
    SRL 15
    ANDI 1
    SLL 15
    STO t0
    LD t1
    SUB t0
    STO v1
    LD v1
    STO $out_port
    HLT
