const maxOddBinaryConstruct = (s) => {
  let ones = -1;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "1") ones++;
  }
  const zeros = s.length - ones - 1;
  return "1".repeat(ones) + "0".repeat(zeros) + "1";
};
