/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"
#include "stdio.h"
#include "string.h"
#include "dma.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "arm_math.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
#define BLOCK_SIZE          1     // Processa um dado por vez na interrupção
#define NUM_TAPS_LP         41    // Número de taps no FIR Passa-Baixo
#define NUM_TAPS_HP         101   // Número de taps no FIR Passa-Alto
#define NUM_TAPS_MA         20    // Número de taps no filtro de Média Móvel



// Buffers de estado e coeficientes dos filtros
float32_t firStateLP[NUM_TAPS_LP + BLOCK_SIZE - 1];
float32_t firStateHP[NUM_TAPS_HP + BLOCK_SIZE - 1];
float32_t firStateMA[NUM_TAPS_MA + BLOCK_SIZE - 1];
float32_t iirStateNotch[4]={0};  // Estado do filtro IIR Notch


// Coeficientes dos filtros (preencher com valores calculados)
float32_t firCoeffsLP[NUM_TAPS_LP] = { -2.49582062811498e-18, -0.000843883995071432, 0.00172480322214108, -0.00231835925473622, 0.00196357837057156, -6.69912201787522e-18, -0.0036046519659237, 0.0077148790607059, -0.010040824322041, 0.00796400731979479, -1.68467892397761e-17, -0.0127268712987161, 0.025823635119039, -0.0323979350039468, 0.0252801324472093, -2.6994456461677e-17, -0.0426821670692607, 0.0958889551620961, -0.148016257409132, 0.186112126299831, 0.80031766663488, 0.186112126299831, -0.148016257409132, 0.0958889551620961, -0.0426821670692607, -2.6994456461677e-17, 0.0252801324472093, -0.0323979350039468, 0.025823635119039, -0.0127268712987161, -1.68467892397761e-17, 0.00796400731979479, -0.010040824322041, 0.0077148790607059, -0.0036046519659237, -6.69912201787522e-18, 0.00196357837057156, -0.00231835925473622, 0.00172480322214108, -0.000843883995071432, -2.49582062811498e-18 };
float32_t firCoeffsHP[NUM_TAPS_HP] = {-0.000157405827432331,-0.000159296208787861,-0.000164756372485308,-0.000173771824085955,-0.000186313716983139,-0.000202338951392229,-0.000221790331446695,-0.000244596779823655,-0.000270673609085908,-0.000299922848691336,-0.000332233626392146,-0.000367482602519124,-0.00040553445542883,-0.000446242416176931,-0.00048944885027906,-0.000534985884221702,-0.000582676074202163,-0.000632333114397873,-0.000683762581902517,-0.000736762715311279,-0.000791125223798025,-0.000846636123397069,-0.000903076597091444,-0.000960223875203619,-0.00101785213250446,-0.00107573339837952,-0.00113363847633987,-0.00119133786912079,-0.00124860270558837,-0.0013052056656613,-0.00136092189946731,-0.00141552993696599,-0.00146881258431719,-0.00152055780331749,-0.00157055957030379,-0.00161861871099773,-0.00166454370786934,-0.00170815147670307,-0.0017492681091829,-0.00178772957844312,-0.00182338240469029,-0.00185608427815808,-0.0018857046368413,-0.00191212519662763,-0.00193524043165451,-0.00195495800291107,-0.00197119913332778,-0.00198389892780654,-0.00199300663688009,-0.00199848586291141,0.998157039286965,-0.00199848586291141,-0.00199300663688009,-0.00198389892780654,-0.00197119913332778,-0.00195495800291107,-0.00193524043165451,-0.00191212519662763,-0.0018857046368413,-0.00185608427815808,-0.00182338240469029,-0.00178772957844312,-0.0017492681091829,-0.00170815147670307,-0.00166454370786934,-0.00161861871099773,-0.00157055957030379,-0.00152055780331749,-0.00146881258431719,-0.00141552993696599,-0.00136092189946731,-0.0013052056656613,-0.00124860270558837,-0.00119133786912079,-0.00113363847633987,-0.00107573339837952,-0.00101785213250446,-0.000960223875203619,-0.000903076597091444,-0.000846636123397069,-0.000791125223798025,-0.000736762715311279,-0.000683762581902517,-0.000632333114397873,-0.000582676074202163,-0.000534985884221702,-0.00048944885027906,-0.000446242416176931,-0.00040553445542883,-0.000367482602519124,-0.000332233626392146,-0.000299922848691336,-0.000270673609085908,-0.000244596779823655,-0.000221790331446695,-0.000202338951392229,-0.000186313716983139,-0.000173771824085955,-0.000164756372485308,-0.000159296208787861,-0.000157405827432331 };
float32_t firCoeffsMA[NUM_TAPS_MA] = {0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05};  // 1/N=1/20=0.05 Coeficientes uniformes para média móvel
float32_t iirCoeffsNotch[5] = { 0.992207063708048, -1.60542475295735, 0.992207063708048, 1.60681611383654, -0.986133944044009};





// Instâncias dos filtros
arm_fir_instance_f32 S_FIR_LP;
arm_fir_instance_f32 S_FIR_HP;
arm_fir_instance_f32 S_FIR_MA;
arm_biquad_casd_df1_inst_f32 S_IIR_Notch;


// Dados de entrada e saída
volatile float32_t inputSample = 0.0f;        // Amostra atual (entrada)
volatile float32_t outputSample = 0.0f;       // Amostra atual (saída)
volatile float32_t tempBuffer1 = 0.0f;        // Buffer temporário 1
volatile float32_t tempBuffer2 = 0.0f;        // Buffer temporário 2

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */



uint32_t amplitude=0;





/* USER CODE END PM */



/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */


/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
static void MX_NVIC_Init(void);

/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

uint8_t TxBuffer[50];

/* USER CODE END 0 */
/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MPU Configuration--------------------------------------------------------*/
  MPU_Config();

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_TIM2_Init();
  MX_USART3_UART_Init();


  /* Initialize interrupts */
  MX_NVIC_Init();
  /* USER CODE BEGIN 2 */
  HAL_ADC_Start_DMA(&hadc1, &amplitude, 1);

  // Inicialização dos filtros FIR
  arm_fir_init_f32(&S_FIR_LP, NUM_TAPS_LP, firCoeffsLP, firStateLP, BLOCK_SIZE);
  arm_fir_init_f32(&S_FIR_HP, NUM_TAPS_HP, firCoeffsHP, firStateHP, BLOCK_SIZE);
  arm_fir_init_f32(&S_FIR_MA, NUM_TAPS_MA, firCoeffsMA, firStateMA, BLOCK_SIZE);
  // Inicialização do filtro IIR Notch
   arm_biquad_cascade_df1_init_f32(&S_IIR_Notch, 1, iirCoeffsNotch, iirStateNotch);


  HAL_TIM_Base_Start_IT(&htim2);


  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {


    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */

  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 8;
  RCC_OscInitStruct.PLL.PLLN = 216;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Activate the Over-Drive mode
  */
  if (HAL_PWREx_EnableOverDrive() != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_7) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief NVIC Configuration.
  * @retval None
  */
static void MX_NVIC_Init(void)
{
  /* ADC_IRQn interrupt configuration */
 // HAL_NVIC_SetPriority(ADC_IRQn, 0, 0);
 // HAL_NVIC_EnableIRQ(ADC_IRQn);
  /* TIM2_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(TIM2_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(TIM2_IRQn);
  /* USART3_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(USART3_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(USART3_IRQn);
}






/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

 /* MPU Configuration */

void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x0;
  MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
  MPU_InitStruct.SubRegionDisable = 0x87;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);
  /* Enables the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);

}





void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim){
	if(htim == &htim2){
		inputSample= amplitude;

		 // Passa-Baixo FIR
		 arm_fir_f32(&S_FIR_LP, &inputSample, &tempBuffer1, BLOCK_SIZE);


		    // Notch IIR
		  arm_biquad_cascade_df1_f32(&S_IIR_Notch, &tempBuffer1, &tempBuffer2, BLOCK_SIZE);

		    // Passa-Alto FIR
		  arm_fir_f32(&S_FIR_HP, &tempBuffer2, &tempBuffer1, BLOCK_SIZE);

		   // Média Móvel FIR
		  arm_fir_f32(&S_FIR_MA, &tempBuffer1, &outputSample, BLOCK_SIZE);

		  uint32_t outputValue = (uint32_t)(outputSample * 1000);
		  sprintf((char *)TxBuffer, "<%lu><%lu>\n\r",outputValue,(uint32_t)inputSample);
		  HAL_UART_Transmit_DMA(&huart3, TxBuffer, strlen((const char *)TxBuffer));






	}
}








/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
