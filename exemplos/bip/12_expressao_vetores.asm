.data
v0 : 0, 0, 0
v1 : 0, 0, 0
v2 : 0
t0 : 0
t1 : 0
t2 : 0
c0 : 32767

.text
    LDI 0
    STO t0
    LDI 20
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 1
    STO t0
    LDI 5
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v1
    LDI 0
    STO $indr
    LDV v0
    STO t0
    LDI 1
    STO $indr
    LDV v1
    ADDI 2
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
    STO v2
    LD v2
    STO $out_port
    HLT
