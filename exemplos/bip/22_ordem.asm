.data
v0 : 0
v1 : 0
v2 : 0
v3 : 0
v4 : 0
v5 : 0
t0 : 0
t1 : 0
c0 : 32767
t2 : 0

.text
    LDI 20
    STO v0
    LDI 5
    STO v1
    LDI 2
    STO v2
    LD v0
    SUB v1
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
    SUB v2
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
    STO v3
    LD v0
    STO t0
    LD v1
    SUB v2
    STO t1
    AND c0
    STO t2
    LD t1
    SRL 15
    ANDI 1
    SLL 15
    STO t1
    LD t2
    SUB t1
    STO t1
    LD t0
    SUB t1
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
    STO v4
    LD v0
    ADD v1
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
    STO t0
    LD v2
    ADDI 1
    STO t1
    AND c0
    STO t2
    LD t1
    SRL 15
    ANDI 1
    SLL 15
    STO t1
    LD t2
    SUB t1
    STO t1
    LD t0
    SUB t1
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
    STO v5
    LD v3
    STO $out_port
    LD v4
    STO $out_port
    LD v5
    STO $out_port
    HLT
