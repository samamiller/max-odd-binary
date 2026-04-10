| size binaryString mob t1 t2 s1 s2 |

size := 10000.

binaryString := ''.

size timesRepeat: [ binaryString := binaryString , (2 atRandom - 1) ].

mob := MaxOddBinary new.

t1 := Time millisecondsToRun: [ 50 timesRepeat: [s1 := mob maxOddBinarySort: binaryString]].

t2 := Time millisecondsToRun: [ 50 timesRepeat: [s2 := mob maxOddBinaryCount: binaryString]].

Transcript clear; show: 'Working....'; cr; cr;
	show: 'Same result is: '; show: s1 = s2; cr; cr;
	show: 'Sort Reverse: '; show: (t1 / 50) asFloat; show: 'ms.'; cr;
	show: 'Counting: '; show: (t2 / 50) asFloat; show: 'ms.'; cr; cr;
	show: 'After 50 iterations of '; show: size
