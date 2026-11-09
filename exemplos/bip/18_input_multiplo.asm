.data
v0 : 0
v1 : 0
v2 : 0, 0, 0, 0, 0
v3 : 0
t0 : 0
t1 : 0
c0 : 32767
t2 : 0

.text
    LDI 2
    STO v3
    LD $in_port
    STO v0
    LD $in_port
    STO v1
    LD v3
    ADDI 1
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
    LD $in_port
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v2
    LD v0
    STO $out_port
    LD v1
    STO $out_port
    LDI 3
    STO $indr
    LDV v2
    STO $out_port
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
    LD v3
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
    STO $indr
    LDV v2
    STO t1
    LD t0
    ADD t1
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
    STO $out_port
    HLT
