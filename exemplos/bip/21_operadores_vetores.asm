.data
v0 : 0, 0, 0
t0 : 0
t1 : 0
c0 : 32767

.text
    LDI 0
    STO t0
    LDI 10
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 1
    STO t0
    LDI 3
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 0
    STO $indr
    LDV v0
    STO t0
    LDI 1
    STO $indr
    LDV v0
    STO t1
    LD t0
    AND t1
    STO $out_port
    LDI 0
    STO $indr
    LDV v0
    STO t0
    LDI 1
    STO $indr
    LDV v0
    STO t1
    LD t0
    OR t1
    STO $out_port
    LDI 0
    STO $indr
    LDV v0
    STO t0
    LDI 1
    STO $indr
    LDV v0
    STO t1
    LD t0
    XOR t1
    STO $out_port
    LDI 0
    STO $indr
    LDV v0
    NOT
    STO $out_port
    LDI 0
    STO $indr
    LDV v0
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
    LDI 0
    STO $indr
    LDV v0
    SRL 1
    AND c0
    STO $out_port
    HLT
