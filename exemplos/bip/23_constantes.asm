.data
v0 : 0
v1 : 0
v2 : 0
c0 : 1024
c1 : 1025
t0 : 0
t1 : 0
c2 : 32767

.text
    LD c0
    STO v0
    LD c1
    NOT
    ADDI 1
    STO t0
    AND c2
    STO t1
    LD t0
    SRL 15
    ANDI 1
    SLL 15
    STO t0
    LD t1
    SUB t0
    STO v1
    LD c2
    STO v2
    LD v0
    STO $out_port
    LD v1
    STO $out_port
    LD v2
    STO $out_port
    LD c2
    STO $out_port
    LDI 10
    STO $out_port
    LDI 10
    STO $out_port
    HLT
