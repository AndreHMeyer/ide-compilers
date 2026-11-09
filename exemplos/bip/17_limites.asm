.data
v0 : 0
v1 : 0
c0 : 32767
c1 : -32768
t0 : 0
t1 : 0
c2 : 16384

.text
    LD c0
    STO v0
    LD c1
    STO v1
    LD v0
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
    STO $out_port
    LD v1
    SUBI 1
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
    LD v1
    NOT
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
    STO $out_port
    LDI 10
    NOT
    STO $out_port
    LDI 1
    NOT
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
    SRL 1
    AND c0
    STO $out_port
    LD c2
    SLL 1
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
    LDI -1
    STO $out_port
    LDI -1
    STO $out_port
    HLT
