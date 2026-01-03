import { Stat, StatLabel, StatNumber, StatHelpText, Icon, HStack, Box } from "@chakra-ui/react";
import { IconType } from "react-icons";

interface StatCardProps {
  label: string;
  value?: string | number;
  icon: IconType;
  trend?: string;
}

export const StatCard = ({ label, value, icon, trend }: StatCardProps) => {
  // Dynamische Farbe basierend auf Trend-Wert
  const getTrendColor = (trendValue: string): string => {
    if (trendValue.includes("+") || trendValue.startsWith("€+")) {
      return "green.400";
    } else if (trendValue.includes("-") || trendValue.startsWith("€-")) {
      return "red.400";
    } else if (trendValue.includes("±0")) {
      return "gray.400";
    }
    return "teal.400"; // Fallback
  };

  return (
    <Box
      className="stat-card fade-in"
      bg="gray.800"
      borderRadius="lg"
      p={4}
      borderWidth="1px"
      borderColor="whiteAlpha.200"
      transition="all 0.3s"
      _hover={{
        transform: "translateY(-4px)",
        boxShadow: "0 8px 20px rgba(56, 178, 172, 0.3)",
        borderColor: "teal.400",
      }}
    >
      <Stat>
        <HStack justify="space-between" mb={2}>
          <StatLabel fontSize="sm" color="gray.400" fontWeight="medium">
            {label}
          </StatLabel>
          <Icon as={icon} color="teal.400" boxSize={5} />
        </HStack>
        <StatNumber fontSize="2xl" fontWeight="bold" color="white" isTruncated>
          {value ?? "—"}
        </StatNumber>
        {trend && (
          <StatHelpText fontSize="xs" color={getTrendColor(trend)} mb={0} fontWeight="semibold">
            {trend}
          </StatHelpText>
        )}
      </Stat>
    </Box>
  );
};
