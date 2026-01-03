import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ChakraProvider, extendTheme } from "@chakra-ui/react";

const config = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  styles: {
    global: {
      body: {
        bg: "transparent", // Let App.css handle background
        color: "whiteAlpha.900",
      },
    },
  },
  colors: {
    // Override Chakra colors to match your design
    brand: {
      50: "#e6fffa",
      100: "#b2f5ea",
      200: "#81e6d9",
      300: "#4fd1c5",
      400: "#38b2ac",
      500: "#319795",
      600: "#2c7a7b",
      700: "#285e61",
      800: "#234e52",
      900: "#1d4044",
    },
  },
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <App />
    </ChakraProvider>
  </React.StrictMode>,
);
