.data
t0 : 0
t1 : 0
c0 : 32767

.text
    LDI 10
    ANDI 3
    STO $out_port
    LDI 10
    ORI 3
    STO $out_port
    LDI 10
    XORI 3
    STO $out_port
    LDI 10
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
    STO $out_port
    LDI 10
    SUBI 3
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
    LDI 5
    SLL 0
    STO $out_port
    LDI 5
    SRL 0
    STO $out_port
    HLT
