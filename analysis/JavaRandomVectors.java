// Independent fixture producer using java.util.Random itself, not a port.
import java.math.BigInteger;
import java.util.Random;

class JavaRandomVectors {
    public static void main(String[] args) {
        long[] seeds = {0L, 12345L, -1L};
        String[] models = {"bigint256", "bigint_i", "bigint_i_minus_1", "int32_be"};
        for (long seed : seeds) {
            for (String model : models) {
                Random random = new Random(seed);
                for (int i = 1; i <= 160; i++) {
                    BigInteger value;
                    if (model.equals("int32_be")) {
                        value = BigInteger.ZERO;
                        for (int j = 0; j < 8; j++) {
                            value = value.shiftLeft(32).or(BigInteger.valueOf(
                                Integer.toUnsignedLong(random.nextInt())));
                        }
                    } else {
                        int width = model.equals("bigint256") ? 256 :
                                    model.equals("bigint_i") ? i : i-1;
                        value = new BigInteger(width, random);
                    }
                    BigInteger top = BigInteger.ONE.shiftLeft(i-1);
                    BigInteger masked = value.and(top.subtract(BigInteger.ONE)).or(top);
                    System.out.println(seed + "," + model + "," + i + "," + masked.toString(16));
                }
            }
        }
    }
}
