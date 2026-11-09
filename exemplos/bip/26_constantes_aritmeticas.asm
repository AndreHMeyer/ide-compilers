.data
t0 : 0
t1 : 0
c0 : 32767
c1 : 16383

.text
    LDI 1
    ADDI 2
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
    LDI 4
    SUBI 6
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
    LDI 20
    SRL 2
    AND c1
    STO $out_port
    LDI 2
    ADDI 3
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
    STO $out_port
    HLT
