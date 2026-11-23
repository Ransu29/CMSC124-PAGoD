BTW Expected output, one line each:
BTW YA RLY
BTW second MEBBE
BTW NO WAI
HAI
WIN
O RLY?
    YA RLY
        VISIBLE "YA RLY"
    MEBBE WIN
        VISIBLE "unexpected MEBBE"
OIC

FAIL
O RLY?
    YA RLY
        VISIBLE "unexpected YA RLY"
    MEBBE BOTH SAEM 2 AN 3
        VISIBLE "unexpected first MEBBE"
    MEBBE BOTH SAEM 2 AN 2
        VISIBLE "second MEBBE"
    MEBBE WIN
        VISIBLE "unexpected third MEBBE"
    NO WAI
        VISIBLE "unexpected NO WAI"
OIC

FAIL
O RLY?
    YA RLY
        VISIBLE "unexpected YA RLY"
    MEBBE FAIL
        VISIBLE "unexpected MEBBE"
    NO WAI
        VISIBLE "NO WAI"
OIC
KTHXBYE
