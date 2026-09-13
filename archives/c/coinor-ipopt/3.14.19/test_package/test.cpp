/* test.cpp — ipopt 3.14.19 consumer test
 *
 * 通过 IPOPT C++ 接口（IpoptApplicationFactory + OptimizeTNLP）求解
 * 一个无约束二次问题：min f(x) = (x0-2)^2 + (x1-3)^2
 * 最优解 x* = (2, 3)，f* = 0。验证库链接、求解器（MUMPS）、
 * 初始化/求解/解提取全链路。
 */
#include <cmath>
#include <cstdio>
#include "IpIpoptApplication.hpp"
#include "IpTNLP.hpp"

using namespace Ipopt;

/** 无约束二次问题 NLP */
class QuadNLP : public TNLP
{
public:
   QuadNLP() : x0_(0.0), x1_(0.0), obj_(0.0) {}

   virtual ~QuadNLP() {}

   /** NLP 规模：2 变量、0 约束、0 非零雅可比、0 非零 Hessian */
   virtual bool get_nlp_info(Index& n, Index& m, Index& nnz_jac_g,
                             Index& nnz_h_lag, IndexStyleEnum& index_style)
   {
      n = 2;
      m = 0;
      nnz_jac_g = 0;
      nnz_h_lag = 0;
      index_style = C_STYLE;
      return true;
   }

   /** 边界：无约束 → [-inf, +inf] */
   virtual bool get_bounds_info(Index n, Number* x_l, Number* x_u,
                                Index m, Number* g_l, Number* g_u)
   {
      for (Index i = 0; i < n; i++) {
         x_l[i] = -1e19;
         x_u[i] =  1e19;
      }
      return true;
   }

   /** 起始点：x = (0, 0) */
   virtual bool get_starting_point(Index n, bool init_x, Number* x,
                                   bool init_z, Number* z_L, Number* z_U,
                                   Index m, bool init_lambda, Number* lambda)
   {
      (void)init_z; (void)z_L; (void)z_U; (void)init_lambda; (void)lambda;
      if (init_x) {
         x[0] = 0.0;
         x[1] = 0.0;
      }
      return true;
   }

   /** 目标函数 f(x) = (x0-2)^2 + (x1-3)^2 */
   virtual bool eval_f(Index n, const Number* x, bool new_x, Number& obj_value)
   {
      (void)n; (void)new_x;
      obj_value = (x[0]-2.0)*(x[0]-2.0) + (x[1]-3.0)*(x[1]-3.0);
      return true;
   }

   /** 梯度 grad_f = (2(x0-2), 2(x1-3)) */
   virtual bool eval_grad_f(Index n, const Number* x, bool new_x, Number* grad_f)
   {
      (void)n; (void)new_x;
      grad_f[0] = 2.0*(x[0]-2.0);
      grad_f[1] = 2.0*(x[1]-3.0);
      return true;
   }

   /** 无约束：约束函数为空 */
   virtual bool eval_g(Index n, const Number* x, bool new_x, Index m, Number* g)
   {
      (void)n; (void)x; (void)new_x; (void)m; (void)g;
      return true;
   }

   /** 无约束：雅可比为空 */
   virtual bool eval_jac_g(Index n, const Number* x, bool new_x,
                           Index m, Index nele_jac, Index* iRow, Index* jCol,
                           Number* values)
   {
      (void)n; (void)x; (void)new_x; (void)m; (void)nele_jac;
      (void)iRow; (void)jCol; (void)values;
      return true;
   }

   /** 无约束：Hessian 为空 */
   virtual bool eval_h(Index n, const Number* x, bool new_x,
                       Number obj_factor, Index m, const Number* lambda,
                       bool new_lambda, Index nele_hess, Index* iRow, Index* jCol,
                       Number* values)
   {
      (void)n; (void)x; (void)new_x; (void)obj_factor;
      (void)m; (void)lambda; (void)new_lambda; (void)nele_hess;
      (void)iRow; (void)jCol; (void)values;
      return true;
   }

   /** 记录最终解 */
   virtual void finalize_solution(
      SolverReturn status, Index n, const Number* x,
      const Number* z_L, const Number* z_U,
      Index m, const Number* g, const Number* lambda,
      Number obj_value, const IpoptData* ip_data,
      IpoptCalculatedQuantities* ip_cq)
   {
      (void)status; (void)z_L; (void)z_U; (void)m; (void)g; (void)lambda;
      (void)ip_data; (void)ip_cq;
      x0_ = x[0];
      x1_ = x[1];
      obj_ = obj_value;
   }

   double x0() const { return x0_; }
   double x1() const { return x1_; }
   double obj() const { return obj_; }

private:
   double x0_, x1_, obj_;
};

int main()
{
   SmartPtr<TNLP> mynlp = new QuadNLP();
   SmartPtr<IpoptApplication> app = IpoptApplicationFactory();

   // 使用 MUMPS 稀疏线性求解器；关闭冗余输出
   app->Options()->SetStringValue("linear_solver", "mumps");
   app->Options()->SetIntegerValue("print_level", 0);
   app->Options()->SetNumericValue("tol", 1e-8);

   ApplicationReturnStatus status = app->Initialize();
   if (status != Solve_Succeeded) {
      std::printf("IPOPT Initialize failed: %d\n", (int)status);
      return (int)status;
   }

   status = app->OptimizeTNLP(mynlp);
   if (status != Solve_Succeeded) {
      std::printf("IPOPT OptimizeTNLP failed: %d\n", (int)status);
      return (int)status;
   }

   QuadNLP* nlp = static_cast<QuadNLP*>(GetRawPtr(mynlp));
   std::printf("Solution: x = (%f, %f), f = %f\n", nlp->x0(), nlp->x1(), nlp->obj());

   // 断言最优解 (2, 3)，f* ≈ 0
   if (std::fabs(nlp->x0() - 2.0) > 1e-4 ||
       std::fabs(nlp->x1() - 3.0) > 1e-4 ||
       std::fabs(nlp->obj() - 0.0) > 1e-6) {
      std::printf("TEST FAILED: unexpected solution\n");
      return 1;
   }
   std::printf("TEST PASSED\n");
   return 0;
}
